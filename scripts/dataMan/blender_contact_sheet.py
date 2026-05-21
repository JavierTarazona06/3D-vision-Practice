#!/usr/bin/env python3
"""
Create a contact sheet image from Blender-rendered PNG views.

This script must be run with Blender's Python interpreter because it uses `bpy`
to load PNG images and write the final contact sheet.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    import sys

    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Create a contact sheet from Blender render outputs.")
    parser.add_argument("--input-dir", type=str, required=True, help="Directory that contains rendered PNG views.")
    parser.add_argument("--output-path", type=str, required=True, help="Path for the generated contact sheet PNG.")
    parser.add_argument("--max-images", type=int, default=5, help="Maximum number of views to place in the grid.")
    parser.add_argument("--columns", type=int, default=3, help="Number of columns in the output grid.")
    return parser.parse_args(argv)


def collect_view_paths(input_dir: Path, max_images: int) -> list[Path]:
    view_paths = sorted(input_dir.glob("view_*.png"))
    if not view_paths:
        raise FileNotFoundError(f"No rendered views found in {input_dir}")
    return view_paths[:max_images]


def build_contact_sheet(view_paths: list[Path], output_path: Path, columns: int) -> None:
    loaded_images = [bpy.data.images.load(str(path.resolve())) for path in view_paths]
    tile_width, tile_height = loaded_images[0].size

    for image in loaded_images[1:]:
        if tuple(image.size) != (tile_width, tile_height):
            raise ValueError("All images must share the same resolution to build the contact sheet.")

    columns = max(1, min(columns, len(loaded_images)))
    rows = math.ceil(len(loaded_images) / columns)
    sheet_width = columns * tile_width
    sheet_height = rows * tile_height
    sheet_pixels = [0.0] * (sheet_width * sheet_height * 4)

    for image_index, image in enumerate(loaded_images):
        col = image_index % columns
        row_from_top = image_index // columns
        row_from_bottom = rows - 1 - row_from_top
        offset_x = col * tile_width
        offset_y = row_from_bottom * tile_height
        image_pixels = list(image.pixels[:])

        for y in range(tile_height):
            src_row_start = y * tile_width * 4
            dest_row_start = ((offset_y + y) * sheet_width + offset_x) * 4
            src_row_end = src_row_start + (tile_width * 4)
            dest_row_end = dest_row_start + (tile_width * 4)
            sheet_pixels[dest_row_start:dest_row_end] = image_pixels[src_row_start:src_row_end]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    contact_sheet = bpy.data.images.new(
        "Multiview_Contact_Sheet",
        width=sheet_width,
        height=sheet_height,
        alpha=True,
    )
    contact_sheet.pixels = sheet_pixels
    contact_sheet.file_format = "PNG"
    contact_sheet.filepath_raw = str(output_path.resolve())
    contact_sheet.save()

    for image in loaded_images:
        bpy.data.images.remove(image)
    bpy.data.images.remove(contact_sheet)


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_path = Path(args.output_path)

    view_paths = collect_view_paths(input_dir=input_dir, max_images=max(1, args.max_images))
    build_contact_sheet(view_paths=view_paths, output_path=output_path, columns=args.columns)
    print(f"[OK] Contact sheet saved: {output_path.resolve()}")


if __name__ == "__main__":
    main()
