#!/usr/bin/env python3
"""
Generate a simple Blender scene and render a random number of camera views.
Default is 10 views, but you can specify more or fewer with the `--num-views` flag.

Scene contents:
- A designed cube on the left side of the X axis.
- A sphere on the right side of the X axis.
- A blue-gray gradient pyramid on one side of the Y axis.
- A forest image used as the world background.
- Area and sun lights.
- Ten cameras placed at random viewpoints around the objects.
- Ten PNG renders saved to an output directory.

Usage example:
    ./blender-local --background --python scripts/dataMan/blender_multiview_scene.py -- \
        --background-image ./assets/blender/img/forest.png \
        --output-dir ./dataset/MultiViewScene/ \
        --seed 42 --resolution 512 --samples 16 \
        --device GPU

    To avoid loading user preferences and addons, which can 
        cause errors on some machines use :
    ./blender-local --background --factory-startup --python scripts/dataMan/blender_multiview_scene.py -- \
        --background-image ./assets/blender/img/forest.png \
        --output-dir ./dataset/MultiViewScene/ \
        --seed 42 --resolution 512 --samples 16 \
        --device GPU
        
Notes:
    This script must be executed with Blender's Python interpreter, not with
    your normal system Python. That is why the command starts with `blender`.

    Blender has 4 main modes ops,context, data and type.
"""
from __future__ import annotations # Delays evaluation of type hints

import argparse # Read flags
import csv
import json
import math
import os
import random
from pathlib import Path
from typing import Any, Iterable

import bpy
from mathutils import Vector


CSV_COLUMNS = [
    "view_serial",
    "image_filename",
    "record_type",
    "name",
    "object_type",
    "primitive_type",
    "location_x",
    "location_y",
    "location_z",
    "rotation_x",
    "rotation_y",
    "rotation_z",
    "scale_x",
    "scale_y",
    "scale_z",
    "lens",
    "sensor_width",
    "clip_start",
    "clip_end",
    "dof_enabled",
    "focus_distance",
    "aperture_fstop",
    "material_name",
    "roughness",
    "metallic",
    "base_color_r",
    "base_color_g",
    "base_color_b",
    "base_color_a",
    "size",
    "segments",
    "ring_count",
    "radius",
    "vertices",
    "radius1",
    "radius2",
    "depth",
    "auto_smooth",
    "auto_smooth_angle",
    "bevel_width",
    "bevel_segments",
    "checker_scale",
    "checker_color1_r",
    "checker_color1_g",
    "checker_color1_b",
    "checker_color1_a",
    "checker_color2_r",
    "checker_color2_g",
    "checker_color2_b",
    "checker_color2_a",
    "gradient_stop0_position",
    "gradient_stop0_r",
    "gradient_stop0_g",
    "gradient_stop0_b",
    "gradient_stop0_a",
    "gradient_stop1_position",
    "gradient_stop1_r",
    "gradient_stop1_g",
    "gradient_stop1_b",
    "gradient_stop1_a",
]


def format_view_serial(view_idx: int) -> str:
    return f"view_{view_idx:03d}"


def vector_to_list(values: Iterable[float]) -> list[float]:
    return [float(value) for value in values]


def color_to_list(values: Iterable[float]) -> list[float]:
    return [float(value) for value in values]


def build_object_metadata(
    obj: bpy.types.Object,
    primitive_type: str,
    material_name: str,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "name": obj.name,
        "object_type": obj.type,
        "primitive_type": primitive_type,
        "location": vector_to_list(obj.location),
        "rotation_euler": vector_to_list(obj.rotation_euler),
        "scale": vector_to_list(obj.scale),
        "material_name": material_name,
    }
    if extra_fields:
        metadata.update(extra_fields)
    return metadata


def prepare_output_directories(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir = output_dir / "img"
    metadata_dir = output_dir / "metadata"
    image_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return image_dir, metadata_dir


def build_camera_metadata(
    camera: bpy.types.Object,
    view_idx: int,
    image_path: Path,
    resolution: int,
) -> dict[str, Any]:
    return {
        "view_serial": format_view_serial(view_idx),
        "image_filename": image_path.name,
        "image_path": str(image_path.resolve()),
        "resolution": [int(resolution), int(resolution)],
        "name": camera.name,
        "object_type": camera.type,
        "location": vector_to_list(camera.location),
        "rotation_euler": vector_to_list(camera.rotation_euler),
        "scale": vector_to_list(camera.scale),
        "lens": float(camera.data.lens),
        "sensor_width": float(camera.data.sensor_width),
        "clip_start": float(camera.data.clip_start),
        "clip_end": float(camera.data.clip_end),
        "dof_enabled": bool(camera.data.dof.use_dof),
        "focus_distance": float(camera.data.dof.focus_distance),
        "aperture_fstop": float(camera.data.dof.aperture_fstop),
    }


def set_xyz_columns(row: dict[str, Any], prefix: str, values: Iterable[float]) -> None:
    x, y, z = [float(value) for value in values]
    row[f"{prefix}_x"] = x
    row[f"{prefix}_y"] = y
    row[f"{prefix}_z"] = z


def set_rgba_columns(row: dict[str, Any], prefix: str, values: Iterable[float]) -> None:
    red, green, blue, alpha = [float(value) for value in values]
    row[f"{prefix}_r"] = red
    row[f"{prefix}_g"] = green
    row[f"{prefix}_b"] = blue
    row[f"{prefix}_a"] = alpha


def metadata_to_csv_row(
    metadata: dict[str, Any],
    *,
    record_type: str,
    view_serial: str,
    image_filename: str,
) -> dict[str, Any]:
    row = {column: "" for column in CSV_COLUMNS}
    row["view_serial"] = view_serial
    row["image_filename"] = image_filename
    row["record_type"] = record_type
    row["name"] = metadata.get("name", "")
    row["object_type"] = metadata.get("object_type", "")
    row["primitive_type"] = metadata.get("primitive_type", "")

    if "location" in metadata:
        set_xyz_columns(row, "location", metadata["location"])
    if "rotation_euler" in metadata:
        set_xyz_columns(row, "rotation", metadata["rotation_euler"])
    if "scale" in metadata:
        set_xyz_columns(row, "scale", metadata["scale"])
    if "base_color" in metadata:
        set_rgba_columns(row, "base_color", metadata["base_color"])
    if "checker_color1" in metadata:
        set_rgba_columns(row, "checker_color1", metadata["checker_color1"])
    if "checker_color2" in metadata:
        set_rgba_columns(row, "checker_color2", metadata["checker_color2"])
    if "gradient_stop0_color" in metadata:
        set_rgba_columns(row, "gradient_stop0", metadata["gradient_stop0_color"])
    if "gradient_stop1_color" in metadata:
        set_rgba_columns(row, "gradient_stop1", metadata["gradient_stop1_color"])

    scalar_fields = (
        "lens",
        "sensor_width",
        "clip_start",
        "clip_end",
        "dof_enabled",
        "focus_distance",
        "aperture_fstop",
        "material_name",
        "roughness",
        "metallic",
        "size",
        "segments",
        "ring_count",
        "radius",
        "vertices",
        "radius1",
        "radius2",
        "depth",
        "auto_smooth",
        "auto_smooth_angle",
        "bevel_width",
        "bevel_segments",
        "checker_scale",
        "gradient_stop0_position",
        "gradient_stop1_position",
    )
    for field in scalar_fields:
        value = metadata.get(field)
        if value is not None:
            row[field] = value

    return row


def export_view_metadata(
    metadata_format: str,
    metadata_dir: Path,
    camera: bpy.types.Object,
    view_idx: int,
    image_path: Path,
    resolution: int,
    object_metadata_by_name: dict[str, dict[str, Any]],
) -> None:
    camera_metadata = build_camera_metadata(
        camera=camera,
        view_idx=view_idx,
        image_path=image_path,
        resolution=resolution,
    )
    view_serial = camera_metadata["view_serial"]
    metadata_path = metadata_dir / f"{view_serial}.{metadata_format}"

    if metadata_format == "json":
        camera_payload = {
            key: value
            for key, value in camera_metadata.items()
            if key not in {"view_serial", "image_filename", "image_path", "resolution"}
        }
        payload = {
            "view_serial": view_serial,
            "image": {
                "filename": camera_metadata["image_filename"],
                "path": camera_metadata["image_path"],
                "resolution": camera_metadata["resolution"],
            },
            "camera": camera_payload,
            "objects": list(object_metadata_by_name.values()),
        }
        with metadata_path.open("w", encoding="utf-8") as metadata_file:
            json.dump(payload, metadata_file, indent=2)
            metadata_file.write("\n")
    else:
        with metadata_path.open("w", newline="", encoding="utf-8") as metadata_file:
            writer = csv.DictWriter(metadata_file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerow(
                metadata_to_csv_row(
                    camera_metadata,
                    record_type="camera",
                    view_serial=view_serial,
                    image_filename=camera_metadata["image_filename"],
                )
            )
            for object_metadata in object_metadata_by_name.values():
                writer.writerow(
                    metadata_to_csv_row(
                        object_metadata,
                        record_type="object",
                        view_serial=view_serial,
                        image_filename=camera_metadata["image_filename"],
                    )
                )

    print(f"[OK] Metadata exported: {metadata_path.resolve()}")


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
        help="Number of Cycles samples per render. Low : 4-8 samples, medium : 16-64 samples, high : 128+ samples.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="AUTO",
        choices=["AUTO", "CPU", "GPU"],
        help=(
            "Cycles device. AUTO keeps Blender's current default. "
            "GPU enables the first detected non-CPU Cycles backend for "
            "the current background session."
        ),
    )
    parser.add_argument(
        "--no-denoise",
        action="store_true", # Noise could be present at low sample counts, but it speeds up rendering significantly.
        help="Disable Cycles denoising for faster renders.",
    )
    parser.add_argument(
        "--metadata-format",
        type=str,
        default="json",
        choices=["json", "csv"],
        help="Per-view metadata export format stored in output-dir/metadata.",
    )
    return parser.parse_args(argv)


def validate_blender_runtime() -> None:
    """
    Stop early when Blender started without a usable OpenColorIO setup.

    A broken color-management startup on this machine produces almost-black
    renders even for bright scenes, so rendering would waste time and disk.
    Blender 2.93 background sessions can also report incomplete enum metadata
    while still exposing valid active color-management settings, so this check
    trusts the active values when they are usable.
    """
    scene = bpy.context.scene
    current_display_device = scene.display_settings.display_device # How colors are displayed, sRGB
    current_view_transform = scene.view_settings.view_transform # How colors are transformed for display
    display_device_items = {
        item.identifier
        # What values are legal for each property
        for item in scene.display_settings.bl_rna.properties["display_device"].enum_items
    }
    view_transform_items = {
        item.identifier
        for item in scene.view_settings.bl_rna.properties["view_transform"].enum_items
    }

    # Search for the config.ocio file at the default Blender datafiles location or in the OCIO environment variable path.
    datafiles_dir = Path(bpy.utils.system_resource("DATAFILES"))
    ocio_env = os.environ.get("OCIO")
    ocio_path = Path(ocio_env).expanduser() if ocio_env else datafiles_dir / "colormanagement" / "config.ocio"

    # Check if settings for device and transform are available and not broken.
    has_usable_display_devices = any(item != "NONE" for item in display_device_items)
    has_usable_view_transforms = any(item != "NONE" for item in view_transform_items)
    has_usable_active_settings = (
        current_display_device not in {"", "NONE"}
        and current_view_transform not in {"", "NONE"}
    )

    # Checks if the config file exists and is usable in background mode.
         # If exists, but not usable, warn.
    if ocio_path.exists() and (
        (has_usable_display_devices and has_usable_view_transforms)
        or has_usable_active_settings
    ):
        if not (has_usable_display_devices and has_usable_view_transforms):
            print(
                "[WARN] Blender reported reduced color-management enum metadata "
                f"in background mode; continuing with active settings "
                f"display_device={current_display_device!r}, "
                f"view_transform={current_view_transform!r}."
            )
        return

    checked_path = ocio_path if ocio_env else datafiles_dir / "colormanagement" / "config.ocio"
    raise RuntimeError(
        "Blender started without a usable OpenColorIO configuration, which will "
        "produce near-black renders. "
        f"Checked OCIO path: {checked_path}. "
        f"Active display device: {current_display_device!r}. "
        f"Active view transform: {current_view_transform!r}. "
        f"Available display devices: {sorted(display_device_items) or ['<none>']}. "
        f"Available view transforms: {sorted(view_transform_items) or ['<none>']}. "
        "Fix Blender's colormanagement files or launch Blender with a valid "
        "`OCIO=/path/to/config.ocio` environment variable before running this script."
    )


def query_cycles_devices(backend: str) -> list[tuple[str, str, str, bool]]:
    """
    Return the devices (GPU, CPU, ...) reported by Cycles for a compute backend.
    Ex. ("NVIDIA GeForce RTX 3070", "CUDA", "GPU", True)

    Unknown backends on older Blender builds simply return an empty list.
    """
    import _cycles

    try:
        return list(_cycles.available_devices(backend))
    except ValueError:
        return []


def configure_cycles_compute_device(requested_device: str) -> None:
    """
    Configure Cycles to use CPU or an auto-detected GPU backend.

    When `requested_device` is `GPU`, this enables the first supported
    non-CPU Cycles backend reported by Blender for the current session.

    args:
        - requested_device: "AUTO", "CPU" or "GPU"
    """
    scene = bpy.context.scene

    # AUTO device, do nothing
    if requested_device == "AUTO":
        print("[INFO] Cycles device: AUTO (keeping Blender default settings)")
        return

    # CPU device, force it and leave
    if requested_device == "CPU":
        scene.cycles.device = "CPU"
        print("[INFO] Cycles device: CPU")
        return

    # GPU device, probe for supported backends and enable the first one with available GPU devices.

    # Check existance of Cycles Add-on
    cycles_addon = bpy.context.preferences.addons.get("cycles")
    if cycles_addon is None:
        raise RuntimeError("Cycles addon is not available, so GPU rendering cannot be configured.")

    # Cycles has the GPu required configuration
    prefs = cycles_addon.preferences
    backend_order = ("CUDA", "OPTIX", "HIP", "ONEAPI", "METAL", "OPENCL")
    probed_backends: list[str] = []

    # Test each backend in order
    for backend in backend_order:
        # For this backend, no devices? Change to next backend. Otherwise we filter not CPU devices
        devices = query_cycles_devices(backend)
        gpu_devices = [device for device in devices if device[1] != "CPU"]
        if not devices:
            continue

        # Store non CPU devices and test next backend if there are not GPU devices
        device_names = ", ".join(name for name, *_ in devices)
        probed_backends.append(f"{backend}: {device_names}")
        if not gpu_devices:
            continue

        # Assign this backend to cycles preferences to be used
        try:
            prefs.compute_device_type = backend
        except (TypeError, ValueError):
            continue

        # For the selected backend, enable all non-CPU devices and store their names for logging.
        prefs.get_devices()
        enabled_gpu_names: list[str] = []
        for device in prefs.devices:
            use_device = getattr(device, "type", "") != "CPU"
            device.use = use_device
            if use_device:
                enabled_gpu_names.append(device.name)

        # We don't have enabled GPUs devices ? Test next Backend
        if not enabled_gpu_names:
            continue

        # We have found at least one GPU device enabled for this backend,
            # we can set it (or them) for cycles and return
        scene.cycles.device = "GPU"
        print(f"[INFO] Cycles GPU backend: {backend}")
        print(f"[INFO] Cycles enabled GPU devices: {', '.join(enabled_gpu_names)}")
        return

    # In this part, no backend has non-CPUs devices to be enabled, so print ERROR
    details = "; ".join(probed_backends) if probed_backends else "<none>"
    raise RuntimeError(
        "No supported Cycles GPU backend was detected for `--device GPU`. "
        f"Cycles backend probe: {details}. Use `--device CPU` or check your "
        "Blender GPU drivers/runtime."
    )


def clear_scene() -> None:
    """
    Remove all existing objects, materials and cameras from the current scene.

    Returns:
        None
    """
    # Remove all objects
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    # Remove all materials, cameras and lights from data

    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)

    for camera in list(bpy.data.cameras):
        bpy.data.cameras.remove(camera)

    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)

    # We want raw 3D scene so we remove compositor postprocessing nodes
        # for render and sequencer for video editing, and disable use of nodes in the scene.
    # Nodes are used as a chain processing approach, so we clear all existing nodes if any, to 
        # avoid unexpected effects on the rendered images.
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

    BSDF : Bidirectional Scattering Distribution Function
    Principled means Blender gives you one practical shader that bundles the 
        most common material controls into one node

    Args:
        name: Material name.
        base_color: RGBA color with values in [0, 1].
        roughness: Surface roughness.
        metallic: Metallic factor.

    Returns:
        bpy.types.Material: Created Blender material.
    """
    material = bpy.data.materials.new(name)
    # Enabled to use the materials shader node tree
    material.use_nodes = True

    # Get Principled BSDF node from the tree or our material
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError("Principled BSDF node was not found.")

    # Set color, roughness and metallic properties to the BSDF node of our material
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return material


def create_checker_cube_material() -> bpy.types.Material:
    """
    Creates a material for the cube with a procedural checkerboard 
        pattern instead of one flat color.

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

    # Create a node with the checker pattern at material tree
        # with name, colors (blue and yellow) and scale (size of the checkers grid) customized.
    checker = nodes.new(type="ShaderNodeTexChecker")
    checker.name = "Procedural_Checker_Design"
    checker.inputs["Scale"].default_value = 8.0
    checker.inputs["Color1"].default_value = (0.05, 0.10, 0.22, 1.0)
    checker.inputs["Color2"].default_value = (1.0, 0.82, 0.20, 1.0)

    # The base color of the BSDF comes from the checker node color
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

    # Create nodes for giving a coordinate system to the object, 
        # separating the axis components and having color in RGB channels rather than one number for color gradient
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    separate_xyz = nodes.new(type="ShaderNodeSeparateXYZ")
    color_ramp = nodes.new(type="ShaderNodeValToRGB")

    # Set the position of the first stop of the ramp at 15%
        # andset color of the first stop to a dark blue
    color_ramp.color_ramp.elements[0].position = 0.15
    color_ramp.color_ramp.elements[0].color = (0.18, 0.28, 0.38, 1.0)  # dark blue-gray
    # Set the position of the second stop of the ramp at 100%
        # andset color of the second stop to a light blue
    color_ramp.color_ramp.elements[1].position = 1.0
    color_ramp.color_ramp.elements[1].color = (0.50, 0.68, 0.86, 1.0)  # light blue

    # The object coordinate become, 
        # separate coordinates of the object
        # take the Z axis and map height to colors (the factor for color map)
            # so the mapping will be the height of the pyramid, and we will have a 
            # vertical gradient where bottom is 0
        # send that color to the material
    links.new(tex_coord.outputs["Generated"], separate_xyz.inputs["Vector"])
    links.new(separate_xyz.outputs["Z"], color_ramp.inputs["Fac"])
    links.new(color_ramp.outputs["Color"], bsdf.inputs["Base Color"])

    bsdf.inputs["Roughness"].default_value = 0.45
    return material


def create_scene_objects() -> tuple[list[bpy.types.Object], dict[str, dict[str, Any]]]:
    """
    Create the cube, sphere, pyramid and ground plane.

    Returns:
        tuple[list[bpy.types.Object], dict[str, dict[str, Any]]]:
        Main scene objects used for camera framing and exportable object metadata.
    """
    object_metadata_by_name: dict[str, dict[str, Any]] = {}

    cube_checker_scale = 8.0
    cube_checker_color1 = (0.05, 0.10, 0.22, 1.0)
    cube_checker_color2 = (1.0, 0.82, 0.20, 1.0)
    cube_roughness = 0.35
    cube_metallic = 0.0
    cube_material = create_checker_cube_material()

    sphere_base_color = (0.85, 0.15, 0.10, 1.0)
    sphere_roughness = 0.42
    sphere_metallic = 0.0
    sphere_material = create_principled_material(
        name="Sphere_Smooth_Red_Material",
        base_color=sphere_base_color,
        roughness=sphere_roughness,
        metallic=sphere_metallic,
    )

    gradient_stop0_position = 0.15
    gradient_stop0_color = (0.18, 0.28, 0.38, 1.0)
    gradient_stop1_position = 1.0
    gradient_stop1_color = (0.50, 0.68, 0.86, 1.0)
    pyramid_roughness = 0.45
    pyramid_metallic = 0.0
    pyramid_material = create_gradient_pyramid_material()

    ground_base_color = (0.12, 0.20, 0.12, 1.0)
    ground_roughness = 0.9
    ground_metallic = 0.0
    ground_material = create_principled_material(
        name="Ground_Matte_Dark_Green",
        base_color=ground_base_color,
        roughness=ground_roughness,
    )

    # Add Cube on the left side of X axis.
    bpy.ops.mesh.primitive_cube_add(size=1.7, location=(-2.2, 0.0, 0.85))
    cube = bpy.context.object
    cube.name = "Designed_Cube_Left_X"
    cube.data.materials.append(cube_material)
    if hasattr(cube.data, "use_auto_smooth"): # If property exists
        cube.data.use_auto_smooth = True # Smooth angles that it consider
        cube.data.auto_smooth_angle = math.radians(60.0) # Edges less sharper than 60 degrees will be smoothed
    for polygon in cube.data.polygons:
        polygon.use_smooth = True # Shade faces smoothly

    # Bevel makes the edges more rounded and visually more realistic.
    # It has a width and segments that control the geometry of the bevel.
    # Weighted normals are used to control the surface normals for better shading taking into account where the
        # Object surface is pointing
    bevel = cube.modifiers.new(name="Small_Bevel_For_Design", type="BEVEL")
    bevel.width = 0.05
    bevel.segments = 2
    cube.modifiers.new(name="Weighted_Normals", type="WEIGHTED_NORMAL")
    object_metadata_by_name[cube.name] = build_object_metadata(
        obj=cube,
        primitive_type="cube",
        material_name=cube_material.name,
        extra_fields={
            "size": 1.7,
            "roughness": cube_roughness,
            "metallic": cube_metallic,
            "auto_smooth": bool(getattr(cube.data, "use_auto_smooth", False)),
            "auto_smooth_angle": float(getattr(cube.data, "auto_smooth_angle", 0.0)),
            "bevel_width": float(bevel.width),
            "bevel_segments": int(bevel.segments),
            "checker_scale": cube_checker_scale,
            "checker_color1": color_to_list(cube_checker_color1),
            "checker_color2": color_to_list(cube_checker_color2),
        },
    )

    # Sphere on the right side of X axis.
        # u and v for latitude and longitude segments, radius for size and location for position in the scene
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64, # Vertical slices, longitude
        ring_count=32, # Horizontal slices, latitude
        radius=0.95,
        location=(2.2, 0.0, 0.95),
    )
    sphere = bpy.context.object
    sphere.name = "Sphere_Right_X"
    sphere.data.materials.append(sphere_material)
    bpy.ops.object.shade_smooth() # Smooth, not faceted
    object_metadata_by_name[sphere.name] = build_object_metadata(
        obj=sphere,
        primitive_type="uv_sphere",
        material_name=sphere_material.name,
        extra_fields={
            "segments": 64,
            "ring_count": 32,
            "radius": 0.95,
            "base_color": color_to_list(sphere_base_color),
            "roughness": sphere_roughness,
            "metallic": sphere_metallic,
        },
    )

    # Pyramid on one side of Y axis.
    # Blender cone with vertices=4 behaves as a square pyramid.
    bpy.ops.mesh.primitive_cone_add(
        vertices=4, # Circular base to cone base
        radius1=1.0,
        radius2=0.0,
        depth=2.0,
        location=(0.0, 2.6, 1.0),
        rotation=(0.0, 0.0, math.radians(45.0)),
    )
    pyramid = bpy.context.object
    pyramid.name = "Blue_Gray_Gradient_Pyramid_Positive_Y"
    pyramid.data.materials.append(pyramid_material)
    object_metadata_by_name[pyramid.name] = build_object_metadata(
        obj=pyramid,
        primitive_type="cone_pyramid",
        material_name=pyramid_material.name,
        extra_fields={
            "vertices": 4,
            "radius1": 1.0,
            "radius2": 0.0,
            "depth": 2.0,
            "roughness": pyramid_roughness,
            "metallic": pyramid_metallic,
            "gradient_stop0_position": gradient_stop0_position,
            "gradient_stop0_color": color_to_list(gradient_stop0_color),
            "gradient_stop1_position": gradient_stop1_position,
            "gradient_stop1_color": color_to_list(gradient_stop1_color),
        },
    )

    # Ground plane.
    bpy.ops.mesh.primitive_plane_add(size=9.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.object
    ground.name = "Ground_Plane"
    ground.data.materials.append(ground_material)
    #bpy.ops.object.shade_smooth() # Blender context dependent
    for polygon in ground.data.polygons:
        polygon.use_smooth = True  # Not really needed for a plane, but we do it for consistency with the other objects
    object_metadata_by_name[ground.name] = build_object_metadata(
        obj=ground,
        primitive_type="plane",
        material_name=ground_material.name,
        extra_fields={
            "size": 9.0,
            "base_color": color_to_list(ground_base_color),
            "roughness": ground_roughness,
            "metallic": ground_metallic,
        },
    )

    return [cube, sphere, pyramid], object_metadata_by_name


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

    # Create a new world or take the existing one and activate nodes, 
        # which allow us to set the background as an image texture.
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    # Nodes for final world and texture/color/light
    output = nodes.new(type="ShaderNodeOutputWorld")
    background = nodes.new(type="ShaderNodeBackground")

    image_node = nodes.new(type="ShaderNodeTexEnvironment")
    image_node.name = "Forest_Background_Image"
    image_node.image = bpy.data.images.load(str(background_image_path.resolve()))

    # Connect image, background and world output to render the background image in the scene
        # and set the brightness of background to a value
    links.new(image_node.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])
    background.inputs["Strength"].default_value = 0.8


def add_lights() -> None:
    """
    Add an area light and a sun light to illuminate the scene.

    Returns:
        None
    """
    # Light types are Point like bulb, area like a panel,
        # sun for a directional lighh and spot like a flaslight (cone of light)
    # Enrgy is the intensity that depends on the type of light
        # sun does not require as much as area light to have a good illumination.
    # Size controls the softness of shadows for area lights, and the angle of the sun for sun lights.
        # More siae, softer shadows.

    # Add a large area light above and in front of the objects, pointing downwards.
    bpy.ops.object.light_add(type="AREA", location=(0.0, -3.5, 6.0))
    area_light = bpy.context.object
    area_light.name = "Large_Soft_Area_Light"
    area_light.data.energy = 650.0
    area_light.data.size = 5.0

    # Add a sun with a moderate intensity and a wide angle for soft shadows.
    # Rotation makes rays come from the upper front right
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
    direction = target - obj.location # Vector from camera to target
    # Make object to look at target by rotation the quaternion direction
        # where the viewing direction of the object is -z
        # and the up direction that must be kept as much as possible is y
        # Then change to traditional euler angles for the object rotation in each dimension
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def compute_target_point(objects: Iterable[bpy.types.Object]) -> Vector:
    """
    Compute a robust camera target from the main scene objects.
    """

    # Define world bounds based on The added objects with mesh, the figures.
        # First, add at the list all the corners of objects transformed to 
        # world coorfinates thanks to the matrix_world of each object, which contains the position, 
        # rotation and scale of the object in the world.
    bounds_world: list[Vector] = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        bounds_world.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)

    if not bounds_world:
        return Vector((0.0, 0.0, 1.0))

    # Get smallest and largest coordinates points by dimension
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

    # Get the midpoint of the bounding box defined by the smallest and largest coordinates,
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
    # Define spherical coordinates to place camera 
        # azimuth is theta the angle in the horizontal plane that should point to target,
        # elevation is phi the angle from the horizontal plane.
        # radius is rho the distance from the target, 
    azimuth = random.uniform(0.0, 2.0 * math.pi)
    elevation = random.uniform(math.radians(18.0), math.radians(55.0))
    radius = random.uniform(radius_min, radius_max)

    # Transform spherical coordinates to Cartesian coordinates for camera position.
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
        # Create camera at random position with radios distance to the target
        position = sample_camera_position(radius_min=5.2, radius_max=7.0)
        bpy.ops.object.camera_add(location=position)
        camera = bpy.context.object
        camera.name = f"Random_View_Camera_{view_idx:03d}" # Padding with 3 digits -> Number is ###

        camera.data.lens = 45.0 # Focal length in mm, more is zoom, less is wide angle
        camera.data.sensor_width = 32.0
        camera.data.clip_start = 0.1 # Objects closer tham this disappear
        camera.data.clip_end = 100.0 # Objects farther than this disappear

        # We activate depth of field to focus on target
            # which menas sharper edges at focus and blurry edges far from focus
            # We set that focus distance and the aperture where focus stop, 
            # higher value, less blur, but also less realistic and more rendering
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
    output_dir.mkdir(parents=True, exist_ok=True) # Create it with parents if it does not exist

    scene = bpy.context.scene
    scene.render.engine = engine

    if engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = use_denoising
        # Enables that number of cycles samples required for a pixel depend on the
            # complexity of the pixel
        if hasattr(scene.cycles, "use_adaptive_sampling"):
            scene.cycles.use_adaptive_sampling = True
        configure_cycles_compute_device(device)

    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    # Enable background, not transparent background
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def render_views(
    cameras: Iterable[bpy.types.Object],
    image_dir: Path,
    metadata_dir: Path,
    metadata_format: str,
    object_metadata_by_name: dict[str, dict[str, Any]],
    resolution: int,
) -> None:
    """
    Render one PNG image for each camera.

    Args:
        cameras: Cameras used for rendering.
        image_dir: Directory where rendered images are saved.
        metadata_dir: Directory where per-view metadata files are saved.
        metadata_format: Export format for metadata files.
        object_metadata_by_name: Static scene object metadata keyed by object name.
        resolution: Square image resolution written alongside the metadata.

    Returns:
        None
    """
    scene = bpy.context.scene

    for view_idx, camera in enumerate(cameras):
        view_serial = format_view_serial(view_idx)
        image_path = image_dir / f"{view_serial}.png"
        scene.camera = camera
        scene.render.filepath = str(image_path.resolve())
        # Update scene
        bpy.context.view_layer.update()
        # write_still makes render to save the image to the filepath defined in scene.render.filepath
        bpy.ops.render.render(write_still=True)
        print(f"[OK] Rendered: {scene.render.filepath}")
        export_view_metadata(
            metadata_format=metadata_format,
            metadata_dir=metadata_dir,
            camera=camera,
            view_idx=view_idx,
            image_path=image_path,
            resolution=resolution,
            object_metadata_by_name=object_metadata_by_name,
        )


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
    image_dir, metadata_dir = prepare_output_directories(output_dir)

    validate_blender_runtime()
    clear_scene()
    scene_objects, object_metadata_by_name = create_scene_objects()
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
    render_views(
        cameras=cameras,
        image_dir=image_dir,
        metadata_dir=metadata_dir,
        metadata_format=args.metadata_format,
        object_metadata_by_name=object_metadata_by_name,
        resolution=args.resolution,
    )


if __name__ == "__main__":
    main()
