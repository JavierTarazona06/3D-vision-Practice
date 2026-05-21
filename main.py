from __future__ import annotations

import shlex
import subprocess
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BLENDER_LOCAL = PROJECT_ROOT / "blender-local"
MULTIVIEW_BACKGROUND = PROJECT_ROOT / "assets" / "blender" / "img" / "forest.png"
MULTIVIEW_OUTPUT_DIR = PROJECT_ROOT / "dataset" / "MultiViewScene"
MULTIVIEW_CONTACT_SHEET = MULTIVIEW_OUTPUT_DIR / "contact_sheet_views.png"


def show_tensors() -> None:
    import torch

    print("===========================")
    print("# Tensors")
    print("===========================")
    x = torch.tensor([1.0, 2.0, 3.0])
    print("A tensor: ", x)


def show_gpu_control() -> None:
    import torch

    print("===========================")
    print("# GPU Control")
    print("===========================")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    x = torch.tensor([1.0, 2.0, 3.0]).to(device)
    print("Device: ", device)
    print("Tensor on device: ", x)


def run_simple_model() -> None:
    from models.SimpleNeuralNetworkModel import SimpleNeuralNetworkModel
    from scripts.training_loop import training_loop

    print("===========================")
    print("# Simple Neural Network Model")
    print("===========================")
    my_model = SimpleNeuralNetworkModel()
    training_loop(my_model)


def run_data_manager() -> None:
    from scripts.dataMan.data_manager import main as data_manager_main

    print("===========================")
    print("# Data Manager")
    print("===========================")
    data_manager_main()


def run_command_and_print(command: list[str], title: str) -> subprocess.CompletedProcess[str]:
    print("===========================")
    print(f"# {title}")
    print("===========================")
    print("Executing command:")
    print(" ", " ".join(shlex.quote(part) for part in command))

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    print("Terminal response:")
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print("[stderr]")
        print(completed.stderr, end="" if completed.stderr.endswith("\n") else "\n")
    if not completed.stdout and not completed.stderr:
        print("<no output>")

    print(f"Exit code: {completed.returncode}")
    return completed


def blender_command_failed(completed: subprocess.CompletedProcess[str]) -> bool:
    combined_output = f"{completed.stdout}\n{completed.stderr}"
    return completed.returncode != 0 or "Traceback (most recent call last):" in combined_output


def collect_fresh_views(started_at_ns: int) -> list[Path]:
    return sorted(
        path
        for path in MULTIVIEW_OUTPUT_DIR.glob("view_*.png")
        if path.stat().st_mtime_ns >= started_at_ns
    )


def run_blender_multiview_scene() -> None:
    print("===========================")
    print("# Blender Multiview Scene")
    print("===========================")

    if not BLENDER_LOCAL.exists():
        print(f"Missing Blender launcher: {BLENDER_LOCAL}")
        return

    if not MULTIVIEW_BACKGROUND.exists():
        print(f"Missing background image: {MULTIVIEW_BACKGROUND}")
        return

    render_command = [
        str(BLENDER_LOCAL),
        "--background",
        "--python",
        "scripts/dataMan/blender_multiview_scene.py",
        "--",
        "--background-image",
        "./assets/blender/img/forest.png",
        "--output-dir",
        "./dataset/MultiViewScene/",
        "--seed",
        "42",
        "--resolution",
        "512",
        "--samples",
        "16",
        "--device",
        "GPU",
    ]
    render_started_at_ns = time.time_ns()
    render_result = run_command_and_print(render_command, "Blender Multiview Render")
    generated_views = collect_fresh_views(render_started_at_ns)

    if blender_command_failed(render_result) or not generated_views:
        print("The exact GPU render command did not produce fresh views.")

        cpu_fallback_command = render_command[:-1] + ["CPU"]
        print("Retrying with CPU so the preview grid can still be generated.")
        render_started_at_ns = time.time_ns()
        render_result = run_command_and_print(cpu_fallback_command, "Blender Multiview Render Fallback")
        generated_views = collect_fresh_views(render_started_at_ns)
        if blender_command_failed(render_result) or not generated_views:
            print("Blender multiview render failed.")
            return

    preview_count = min(6, len(generated_views))
    contact_sheet_command = [
        str(BLENDER_LOCAL),
        "--background",
        "--python",
        "scripts/dataMan/blender_contact_sheet.py",
        "--",
        "--input-dir",
        "./dataset/MultiViewScene/",
        "--output-path",
        "./dataset/MultiViewScene/contact_sheet_views.png",
        "--max-images",
        str(preview_count),
    ]
    contact_sheet_result = run_command_and_print(contact_sheet_command, "Blender Contact Sheet")
    if blender_command_failed(contact_sheet_result):
        print("Contact sheet generation failed.")
        return

    print(f"Rendered {len(generated_views)} views to {MULTIVIEW_OUTPUT_DIR}")
    print(f"Saved n-view preview grid to {MULTIVIEW_CONTACT_SHEET}")


def main() -> int:
    while True:
        print("===========================")
        print("# Menu")
        print("===========================")
        print("0. Exit")
        print("1. Tensors")
        print("2. GPU Control")
        print("3. Simple Neural Network Model")
        print("4. Data Manager")
        print("5. Blender Multiview Scene")

        choice = input("Select an option (0-5): ").strip()

        if choice == "0":
            break
        if choice == "1":
            show_tensors()
            continue
        if choice == "2":
            show_gpu_control()
            continue
        if choice == "3":
            run_simple_model()
            continue
        if choice == "4":
            run_data_manager()
            continue
        if choice == "5":
            run_blender_multiview_scene()
            continue

        print("Invalid option.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
