#!/usr/bin/env python3
"""
Generate a simple Blender scene and render 10 random camera views.

Scene contents:
- A designed cube on the left side of the X axis.
- A sphere on the right side of the X axis.
- A blue-gray gradient pyramid on one side of the Y axis.
- A forest image used as the world background.
- Area and sun lights.
- Ten cameras placed at random viewpoints around the objects.
- Ten PNG renders saved to an output directory.

Usage example:
    blender --background --python scripts/dataMan/blender_multiview_scene.py -- \
        --background-image ./assets/blender/img/forest.png \
        --output-dir ./dataset/MultiViewScene/ \
        --seed 42

    Add --factory-startup at position 2 to avoid loading user preferences and addons, which can cause errors on some machines.

Notes:
    This script must be executed with Blender's Python interpreter, not with
    your normal system Python. That is why the command starts with `blender`.
"""
# TODO 
# Right Blender Download, at project
# Check blender detects GPU
from __future__ import annotations # Delays evaluation of type hints

import argparse # Read flags
import math
import os
import random
from pathlib import Path
from typing import Iterable

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments passed after Blender's `--` separator.

    Returns:
        argparse.Namespace: Parsed arguments containing background image path,
        output directory, number of views, seed, resolution and render engine.
    """
    import sys

    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Create Blender scene and render multiview images.")
    parser.add_argument(
        "--background-image",
        type=str,
        required=True,
        help="Path to the forest background image, for example ./forest.png.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="renders",
        help="Directory where PNG renders will be saved.",
    )
    parser.add_argument(
        "--num-views",
        type=int,
        default=10,
        help="Number of random camera views to render.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible camera positions.",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=1024,
        help="Square render resolution in pixels.",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default="CYCLES",
        choices=["CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"],
        help="Render engine. Use CYCLES for quality, EEVEE for speed.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=64,
        help="Number of Cycles samples per render.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="AUTO",
        choices=["AUTO", "CPU", "GPU"],
        help="Cycles device. AUTO keeps Blender's current default.",
    )
    parser.add_argument(
        "--no-denoise",
        action="store_true",
        help="Disable Cycles denoising for faster renders.",
    )
    return parser.parse_args(argv)


def validate_blender_runtime() -> None:
    """
    Stop early when Blender started without a usable OpenColorIO setup.

    A broken color-management startup on this machine produces almost-black
    renders even for bright scenes, so rendering would waste time and disk.
    """
    scene = bpy.context.scene
    view_transform_items = {
        item.identifier
        for item in scene.view_settings.bl_rna.properties["view_transform"].enum_items
    }

    datafiles_dir = Path(bpy.utils.system_resource("DATAFILES"))
    ocio_env = os.environ.get("OCIO")
    ocio_path = Path(ocio_env).expanduser() if ocio_env else datafiles_dir / "colormanagement" / "config.ocio"

    has_usable_view_transforms = any(item != "NONE" for item in view_transform_items)
    if has_usable_view_transforms and ocio_path.exists():
        return

    checked_path = ocio_path if ocio_env else datafiles_dir / "colormanagement" / "config.ocio"
    raise RuntimeError(
        "Blender started without a usable OpenColorIO configuration, which will "
        "produce near-black renders. "
        f"Checked OCIO path: {checked_path}. "
        f"Available view transforms: {sorted(view_transform_items) or ['<none>']}. "
        "Fix Blender's colormanagement files or launch Blender with a valid "
        "`OCIO=/path/to/config.ocio` environment variable before running this script."
    )


def clear_scene() -> None:
    """
    Remove all existing objects, materials and cameras from the current scene.

    Returns:
        None
    """
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)

    for camera in list(bpy.data.cameras):
        bpy.data.cameras.remove(camera)

    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)

    scene = bpy.context.scene
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.use_nodes = False


def create_principled_material(
    name: str,
    base_color: tuple[float, float, float, float],
    roughness: float = 0.5,
    metallic: float = 0.0,
) -> bpy.types.Material:
    """
    Create a simple Principled BSDF material.

    Args:
        name: Material name.
        base_color: RGBA color with values in [0, 1].
        roughness: Surface roughness.
        metallic: Metallic factor.

    Returns:
        bpy.types.Material: Created Blender material.
    """
    material = bpy.data.materials.new(name)
    material.use_nodes = True

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError("Principled BSDF node was not found.")

    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return material


def create_checker_cube_material() -> bpy.types.Material:
    """
    Create a procedural checker material for the cube design.

    Returns:
        bpy.types.Material: Material with checker texture connected to base color.
    """
    material = bpy.data.materials.new("Cube_Designed_Checker_Material")
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError("Principled BSDF node was not found.")

    checker = nodes.new(type="ShaderNodeTexChecker")
    checker.name = "Procedural_Checker_Design"
    checker.inputs["Scale"].default_value = 8.0
    checker.inputs["Color1"].default_value = (0.05, 0.10, 0.22, 1.0)
    checker.inputs["Color2"].default_value = (1.0, 0.82, 0.20, 1.0)

    links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.35
    return material


def create_gradient_pyramid_material() -> bpy.types.Material:
    """
    Create a blue-gray vertical gradient material for the pyramid.

    Returns:
        bpy.types.Material: Gradient material using shader nodes.
    """
    material = bpy.data.materials.new("Pyramid_Blue_Gray_Gradient_Material")
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError("Principled BSDF node was not found.")

    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    separate_xyz = nodes.new(type="ShaderNodeSeparateXYZ")
    color_ramp = nodes.new(type="ShaderNodeValToRGB")

    color_ramp.color_ramp.elements[0].position = 0.15
    color_ramp.color_ramp.elements[0].color = (0.18, 0.28, 0.38, 1.0)  # dark blue-gray
    color_ramp.color_ramp.elements[1].position = 1.0
    color_ramp.color_ramp.elements[1].color = (0.50, 0.68, 0.86, 1.0)  # light blue

    links.new(tex_coord.outputs["Generated"], separate_xyz.inputs["Vector"])
    links.new(separate_xyz.outputs["Z"], color_ramp.inputs["Fac"])
    links.new(color_ramp.outputs["Color"], bsdf.inputs["Base Color"])

    bsdf.inputs["Roughness"].default_value = 0.45
    return material


def create_scene_objects() -> list[bpy.types.Object]:
    """
    Create the cube, sphere, pyramid and ground plane.

    Returns:
        list[bpy.types.Object]: Main scene objects used for camera framing.
    """
    cube_material = create_checker_cube_material()
    sphere_material = create_principled_material(
        name="Sphere_Smooth_Red_Material",
        base_color=(0.85, 0.15, 0.10, 1.0),
        roughness=0.42,
        metallic=0.0,
    )
    pyramid_material = create_gradient_pyramid_material()
    ground_material = create_principled_material(
        name="Ground_Matte_Dark_Green",
        base_color=(0.12, 0.20, 0.12, 1.0),
        roughness=0.9,
    )

    # Cube on the left side of X axis.
    bpy.ops.mesh.primitive_cube_add(size=1.7, location=(-2.2, 0.0, 0.85))
    cube = bpy.context.object
    cube.name = "Designed_Cube_Left_X"
    cube.data.materials.append(cube_material)
    if hasattr(cube.data, "use_auto_smooth"):
        cube.data.use_auto_smooth = True
        cube.data.auto_smooth_angle = math.radians(60.0)
    for polygon in cube.data.polygons:
        polygon.use_smooth = True

    bevel = cube.modifiers.new(name="Small_Bevel_For_Design", type="BEVEL")
    bevel.width = 0.05
    bevel.segments = 2
    cube.modifiers.new(name="Weighted_Normals", type="WEIGHTED_NORMAL")

    # Sphere on the right side of X axis.
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64,
        ring_count=32,
        radius=0.95,
        location=(2.2, 0.0, 0.95),
    )
    sphere = bpy.context.object
    sphere.name = "Sphere_Right_X"
    sphere.data.materials.append(sphere_material)
    bpy.ops.object.shade_smooth()

    # Pyramid on one side of Y axis.
    # Blender cone with vertices=4 behaves as a square pyramid.
    bpy.ops.mesh.primitive_cone_add(
        vertices=4,
        radius1=1.0,
        radius2=0.0,
        depth=2.0,
        location=(0.0, 2.6, 1.0),
        rotation=(0.0, 0.0, math.radians(45.0)),
    )
    pyramid = bpy.context.object
    pyramid.name = "Blue_Gray_Gradient_Pyramid_Positive_Y"
    pyramid.data.materials.append(pyramid_material)

    # Ground plane.
    bpy.ops.mesh.primitive_plane_add(size=9.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.object
    ground.name = "Ground_Plane"
    ground.data.materials.append(ground_material)
    bpy.ops.object.shade_smooth()

    return [cube, sphere, pyramid]


def set_world_background(background_image_path: Path) -> None:
    """
    Use a PNG/JPG image as the world background.

    Args:
        background_image_path: Path to the background image.

    Returns:
        None

    Raises:
        FileNotFoundError: If the image path does not exist.
    """
    if not background_image_path.exists():
        raise FileNotFoundError(f"Background image not found: {background_image_path}")

    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputWorld")
    background = nodes.new(type="ShaderNodeBackground")

    image_node = nodes.new(type="ShaderNodeTexEnvironment")
    image_node.name = "Forest_Background_Image"
    image_node.image = bpy.data.images.load(str(background_image_path.resolve()))

    links.new(image_node.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])
    background.inputs["Strength"].default_value = 0.8


def add_lights() -> None:
    """
    Add an area light and a sun light to illuminate the scene.

    Returns:
        None
    """
    bpy.ops.object.light_add(type="AREA", location=(0.0, -3.5, 6.0))
    area_light = bpy.context.object
    area_light.name = "Large_Soft_Area_Light"
    area_light.data.energy = 650.0
    area_light.data.size = 5.0

    bpy.ops.object.light_add(type="SUN", location=(0.0, 0.0, 5.0))
    sun = bpy.context.object
    sun.name = "Soft_Sun_Light"
    sun.data.energy = 1.4
    sun.rotation_euler = (math.radians(45.0), 0.0, math.radians(25.0))


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    """
    Rotate an object so that its local -Z axis points toward a target.

    Args:
        obj: Object to rotate, usually a camera.
        target: Target location.

    Returns:
        None
    """
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def compute_target_point(objects: Iterable[bpy.types.Object]) -> Vector:
    """
    Compute a robust camera target from the main scene objects.
    """
    bounds_world: list[Vector] = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        bounds_world.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)

    if not bounds_world:
        return Vector((0.0, 0.0, 1.0))

    min_corner = Vector((
        min(point.x for point in bounds_world),
        min(point.y for point in bounds_world),
        min(point.z for point in bounds_world),
    ))
    max_corner = Vector((
        max(point.x for point in bounds_world),
        max(point.y for point in bounds_world),
        max(point.z for point in bounds_world),
    ))
    return (min_corner + max_corner) * 0.5


def sample_camera_position(radius_min: float, radius_max: float) -> Vector:
    """
    Sample a random camera position around the scene.

    Args:
        radius_min: Minimum distance from the target.
        radius_max: Maximum distance from the target.

    Returns:
        Vector: Random 3D camera position.
    """
    radius = random.uniform(radius_min, radius_max)
    azimuth = random.uniform(0.0, 2.0 * math.pi)
    elevation = random.uniform(math.radians(18.0), math.radians(55.0))

    x = radius * math.cos(elevation) * math.cos(azimuth)
    y = radius * math.cos(elevation) * math.sin(azimuth)
    z = radius * math.sin(elevation)

    return Vector((x, y, z))


def add_random_cameras(num_views: int, seed: int, target: Vector) -> list[bpy.types.Object]:
    """
    Add multiple cameras around the objects.

    Args:
        num_views: Number of cameras to create.
        seed: Random seed.

    Returns:
        list[bpy.types.Object]: Created camera objects.
    """
    random.seed(seed)
    cameras: list[bpy.types.Object] = []

    for view_idx in range(num_views):
        position = sample_camera_position(radius_min=5.2, radius_max=7.0)
        bpy.ops.object.camera_add(location=position)
        camera = bpy.context.object
        camera.name = f"Random_View_Camera_{view_idx:03d}"
        camera.data.lens = 45.0
        camera.data.sensor_width = 32.0
        camera.data.clip_start = 0.1
        camera.data.clip_end = 100.0
        camera.data.dof.use_dof = True
        camera.data.dof.focus_distance = (camera.location - target).length
        camera.data.dof.aperture_fstop = 7.5
        look_at(camera, target)
        cameras.append(camera)

    return cameras


def configure_render_settings(
    output_dir: Path,
    resolution: int,
    engine: str,
    samples: int,
    device: str,
    use_denoising: bool,
) -> None:
    """
    Configure render engine, output format and resolution.

    Args:
        output_dir: Directory for generated images.
        resolution: Square image resolution.
        engine: Blender render engine name.
        samples: Cycles sample count.
        device: Cycles compute device.
        use_denoising: Whether Cycles denoising is enabled.

    Returns:
        None
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    scene.render.engine = engine

    if engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = use_denoising
        if hasattr(scene.cycles, "use_adaptive_sampling"):
            scene.cycles.use_adaptive_sampling = True
        if device != "AUTO":
            scene.cycles.device = device

    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def render_views(cameras: Iterable[bpy.types.Object], output_dir: Path) -> None:
    """
    Render one PNG image for each camera.

    Args:
        cameras: Cameras used for rendering.
        output_dir: Directory where images are saved.

    Returns:
        None
    """
    scene = bpy.context.scene

    for view_idx, camera in enumerate(cameras):
        scene.camera = camera
        scene.render.filepath = str((output_dir / f"view_{view_idx:03d}.png").resolve())
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        print(f"[OK] Rendered: {scene.render.filepath}")


def save_blend_file(output_dir: Path) -> None:
    """
    Save the generated scene as a .blend file.

    Args:
        output_dir: Directory where the scene file is saved.

    Returns:
        None
    """
    blend_path = output_dir / "generated_multiview_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path.resolve()))
    print(f"[OK] Saved Blender scene: {blend_path}")


def main() -> None:
    """
    Build the complete scene and render the requested camera views.

    Returns:
        None
    """
    args = parse_args()
    background_image_path = Path(args.background_image)
    output_dir = Path(args.output_dir)

    validate_blender_runtime()
    clear_scene()
    scene_objects = create_scene_objects()
    set_world_background(background_image_path)
    add_lights()
    target = compute_target_point(scene_objects)
    cameras = add_random_cameras(num_views=args.num_views, seed=args.seed, target=target)
    configure_render_settings(
        output_dir=output_dir,
        resolution=args.resolution,
        engine=args.engine,
        samples=args.samples,
        device=args.device,
        use_denoising=not args.no_denoise,
    )
    save_blend_file(output_dir)
    render_views(cameras=cameras, output_dir=output_dir)


if __name__ == "__main__":
    main()
