# 3D Vision Practice

## Installation

This project provides a `conda` environment definition in [environment.yml](environment.yml).

### Prerequisites

- Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda.
- Open a terminal in the project root.

### Create the environment

The exported `environment.yml` currently contains a machine-specific `prefix:` entry. If you are installing on a different machine, remove the last `prefix:` line from `environment.yml` before creating the environment.

Then create the environment with:

```bash
conda env create -f environment.yml
```

This creates the `3D-vision-practice` environment.

### Activate the environment

```bash
conda activate 3D-vision-practice
```

## Install Blender In The Project Root

For this project, prefer a portable Blender installed directly in the repository
instead of the system `blender` package.

Recommended version:

- `blender-2.93.18-linux-x64`

Why:

- it keeps the Blender version fixed for the project
- it avoids machine-specific issues with the system Blender installation
- it makes the render commands reproducible across this environment

### Expected layout

Extract Blender in the project root so the tree looks like this:

```text
3D-vision-Practice/
├── blender-2.93.18-linux-x64/
├── scripts/
├── assets/
├── dataset/
├── environment.yml
└── README.md
```

### Download and extract

Download `blender-2.93.18-linux-x64` from the official Blender releases, then
extract it in the project root.

If the archive is already downloaded, from the project root run:

```bash
tar -xvf blender-2.93.18-linux-x64.tar.xz
```

### Make Blender executable

After extraction, make the local Blender binaries executable:

```bash
chmod +x blender-2.93.18-linux-x64/blender
chmod +x blender-2.93.18-linux-x64/blender-softwaregl
```

### Relate Blender to this project

After activating the `conda` environment, expose the project-local Blender in
the current shell:

```bash
conda activate 3D-vision-practice
export PROJECT_ROOT="$(pwd)"
export BLENDER_BIN="$PROJECT_ROOT/blender-2.93.18-linux-x64/blender"
```

Check that the project uses the expected Blender binary:

```bash
"$BLENDER_BIN" --version
```

If you always work from the project root, you can also use the binary directly:

```bash
./blender-2.93.18-linux-x64/blender --version
```

## Use Blender In This Environment

### Run the multiview scene generator

From the project root, with the `3D-vision-practice` environment activated:

```bash
conda activate 3D-vision-practice
export BLENDER_BIN="$(pwd)/blender-2.93.18-linux-x64/blender"

"$BLENDER_BIN" --background --factory-startup \
  --python scripts/dataMan/blender_multiview_scene.py -- \
  --background-image ./assets/blender/img/forest.png \
  --output-dir ./dataset/MultiViewScene/ \
  --seed 42 \
  --resolution 512 \
  --samples 16 \
  --device CPU
```

Notes:

- `--factory-startup` avoids interference from user Blender preferences
- `--samples 16` is a good starting point for quick tests
- `--device CPU` is the safe default; switch to `GPU` only after Blender
  correctly detects a supported Cycles GPU backend on your machine

### Optional shell shortcut

If you want a short project-local command, still from the project root:

```bash
ln -sf blender-2.93.18-linux-x64/blender blender-local
./blender-local --version
```

### Update an existing environment

If the environment already exists and you want to sync it with `environment.yml`, run:

```bash
conda env update -f environment.yml --prune
```

## Run the project

After activating the environment, start the project with:

```bash
python main.py
```
