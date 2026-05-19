#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="3D-vision-practice"
PREFERRED_BLENDER_ARCHIVE="blender-2.93.18-linux-x64.tar.xz"
PREFERRED_BLENDER_DIR="blender-2.93.18-linux-x64"
FALLBACK_BLENDER_URL="https://download.blender.org/release/Blender5.1/blender-5.1.1-linux-x64.tar.xz"
FALLBACK_BLENDER_ARCHIVE="$(basename "${FALLBACK_BLENDER_URL%/}")"
DEFAULT_MINICONDA_DIR="$HOME/miniconda3"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT_PATH="$(cd "$SCRIPT_DIR/.." && pwd)"

CUSTOM_BLENDER_PATH=""
CONDA_BASE=""
BLENDER_INSTALL_DIR=""
BLENDER_BIN_PATH=""

log() {
    printf '[setup] %s\n' "$*"
}

warn() {
    printf '[setup][warn] %s\n' "$*" >&2
}

die() {
    printf '[setup][error] %s\n' "$*" >&2
    exit 1
}

capture_checked_output() {
    local output

    if ! output="$("$@" 2>&1)"; then
        printf '%s\n' "$output" >&2
        return 1
    fi

    [[ -n "$output" ]] || return 1
    printf '%s\n' "$output"
}

require_output_contains() {
    local description="$1"
    local expected_fragment="$2"
    shift 2

    local output
    log "$description"
    output="$(capture_checked_output "$@")" || die "Command failed or produced empty output: $*"
    printf '%s\n' "$output"

    [[ "$output" == *"$expected_fragment"* ]] || die "Unexpected output from $*: expected to find '$expected_fragment'."
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Prepare this project on a Linux machine by:
  - installing Miniconda if conda is missing
  - creating or updating the ${ENV_NAME} environment from environment.yml
  - using a project-local Blender build, a user-provided Blender path, or a
    downloaded fallback Blender archive
  - registering PROJECT_ROOT and BLENDER_BIN in the conda environment
  - verifying PyTorch imports/runtime details and Blender command output
  - creating the project-local blender-local symlink

Examples:
  $(basename "$0")
  $(basename "$0") --blender-path /path/to/blender-2.93.18-linux-x64.tar.xz
  $(basename "$0") --blender-path /path/to/blender-2.93.18-linux-x64

Notes:
  - The preferred local Blender archive is ${PREFERRED_BLENDER_ARCHIVE}.
  - If the preferred archive is missing, the script uses --blender-path when
    provided; otherwise it downloads ${FALLBACK_BLENDER_ARCHIVE}.
  - PyTorch verification accepts CPU-only machines and reports CUDA details
    only when torch detects a usable CUDA device.

Options:
  --blender-path PATH   Path to a Blender archive (.tar.xz) or an extracted
                        Blender directory to use if the preferred local
                        Blender archive or extracted directory is unavailable.
  -h, --help            Show this help message and exit.
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --blender-path)
                [[ $# -ge 2 ]] || die "--blender-path requires a value."
                CUSTOM_BLENDER_PATH="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                die "Unknown argument: $1"
                ;;
        esac
    done
}

resolve_path() {
    local input_path="$1"

    if [[ -d "$input_path" ]]; then
        (
            cd "$input_path"
            pwd
        )
        return 0
    fi

    if [[ -e "$input_path" ]]; then
        local parent_dir
        parent_dir="$(cd "$(dirname "$input_path")" && pwd)"
        printf '%s/%s\n' "$parent_dir" "$(basename "$input_path")"
        return 0
    fi

    return 1
}

download_file() {
    local url="$1"
    local output_path="$2"

    if command -v curl >/dev/null 2>&1; then
        if curl --fail --location --retry 5 --retry-delay 2 --retry-all-errors --continue-at - "$url" -o "$output_path"; then
            return 0
        fi

        warn "curl failed while downloading $url. Trying wget instead."
    fi

    if command -v wget >/dev/null 2>&1; then
        if wget --tries=5 --waitretry=2 -O "$output_path" "$url"; then
            return 0
        fi
    fi

    die "Failed to download $url. Re-running the setup may resume any partial download left on disk."
}

is_valid_tar_archive() {
    local archive_path="$1"

    [[ -f "$archive_path" ]] || return 1
    tar -tf "$archive_path" >/dev/null 2>&1
}

download_blender_archive() {
    local url="$1"
    local output_path="$2"
    local partial_path

    partial_path="${output_path}.partial"
    download_file "$url" "$partial_path"

    if ! is_valid_tar_archive "$partial_path"; then
        die "Downloaded file from $url is not a valid tar archive. The remote endpoint may have returned an HTML page instead of Blender."
    fi

    mv -f "$partial_path" "$output_path"
}

source_conda_shell() {
    local conda_sh="$CONDA_BASE/etc/profile.d/conda.sh"

    [[ -f "$conda_sh" ]] || die "Could not find $conda_sh."
    # shellcheck disable=SC1090
    source "$conda_sh"
}

install_miniconda() {
    local arch installer_url installer_path

    arch="$(uname -m)"
    case "$arch" in
        x86_64)
            installer_url="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
            ;;
        aarch64|arm64)
            installer_url="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"
            ;;
        *)
            die "Unsupported architecture for Miniconda installation: $arch"
            ;;
    esac

    installer_path="$PROJECT_ROOT_PATH/$(basename "$installer_url")"

    log "Conda was not found. Installing Miniconda into $DEFAULT_MINICONDA_DIR."
    download_file "$installer_url" "$installer_path"
    bash "$installer_path" -b -p "$DEFAULT_MINICONDA_DIR"

    CONDA_BASE="$DEFAULT_MINICONDA_DIR"
    source_conda_shell
    conda init bash >/dev/null 2>&1 || warn "conda init bash failed. You may need to run it manually later."
}

ensure_conda() {
    if command -v conda >/dev/null 2>&1; then
        CONDA_BASE="$(conda info --base 2>/dev/null || true)"
    fi

    if [[ -z "$CONDA_BASE" ]]; then
        for candidate_prefix in "$DEFAULT_MINICONDA_DIR" "$HOME/anaconda3"; do
            if [[ -x "$candidate_prefix/bin/conda" ]]; then
                CONDA_BASE="$("$candidate_prefix/bin/conda" info --base 2>/dev/null || true)"
                [[ -n "$CONDA_BASE" ]] && break
            fi
        done
    fi

    if [[ -z "$CONDA_BASE" ]]; then
        install_miniconda
        return 0
    fi

    log "Using Conda installation at $CONDA_BASE."
    source_conda_shell
}

prepare_environment_file() {
    local clean_env_file="$1"

    awk 'index($0, "prefix:") != 1 { print }' "$PROJECT_ROOT_PATH/environment.yml" > "$clean_env_file"
}

environment_exists() {
    conda env list | awk 'NF && $1 !~ /^#/ { print $1 }' | grep -Fxq "$ENV_NAME"
}

create_or_update_environment() {
    local clean_env_file
    clean_env_file="$(mktemp)"
    prepare_environment_file "$clean_env_file"

    if environment_exists; then
        log "Conda environment $ENV_NAME already exists. Updating it."
        conda env update -n "$ENV_NAME" -f "$clean_env_file" --prune
    else
        log "Creating conda environment $ENV_NAME from environment.yml."
        conda env create -f "$clean_env_file"
    fi

    rm -f "$clean_env_file"

    log "Activating conda environment $ENV_NAME."
    conda activate "$ENV_NAME"
    [[ "${CONDA_DEFAULT_ENV:-}" == "$ENV_NAME" ]] || die "Conda environment $ENV_NAME is not active after conda activate."
}

archive_root_dir_name() {
    local archive_path="$1"

    tar -tf "$archive_path" | awk -F/ '
        {
            gsub(/^\.\//, "", $0)
        }
        NF && first == "" {
            first = $1
            print first
        }
        END {
            if (first == "") {
                exit 1
            }
        }
    '
}

extract_blender_archive() {
    local archive_path="$1"
    local root_dir_name

    is_valid_tar_archive "$archive_path" || die "Blender archive is invalid or corrupted: $archive_path"
    root_dir_name="$(archive_root_dir_name "$archive_path")"
    [[ -n "$root_dir_name" ]] || die "Could not determine archive root directory for $archive_path."

    if [[ ! -d "$PROJECT_ROOT_PATH/$root_dir_name" ]]; then
        log "Extracting $(basename "$archive_path") into $PROJECT_ROOT_PATH."
        tar -xf "$archive_path" -C "$PROJECT_ROOT_PATH"
    else
        log "Using existing extracted Blender directory $PROJECT_ROOT_PATH/$root_dir_name."
    fi

    BLENDER_INSTALL_DIR="$PROJECT_ROOT_PATH/$root_dir_name"
}

select_blender_installation() {
    local preferred_archive_path custom_path fallback_archive_path

    preferred_archive_path="$PROJECT_ROOT_PATH/$PREFERRED_BLENDER_ARCHIVE"
    fallback_archive_path="$PROJECT_ROOT_PATH/$FALLBACK_BLENDER_ARCHIVE"

    if [[ -d "$PROJECT_ROOT_PATH/$PREFERRED_BLENDER_DIR" ]]; then
        BLENDER_INSTALL_DIR="$PROJECT_ROOT_PATH/$PREFERRED_BLENDER_DIR"
        log "Using existing Blender directory $BLENDER_INSTALL_DIR."
        return 0
    fi

    if [[ -f "$preferred_archive_path" ]]; then
        is_valid_tar_archive "$preferred_archive_path" || die "Preferred Blender archive is invalid or corrupted: $preferred_archive_path"
        log "Found preferred Blender archive $preferred_archive_path."
        extract_blender_archive "$preferred_archive_path"
        return 0
    fi

    if [[ -n "$CUSTOM_BLENDER_PATH" ]]; then
        custom_path="$(resolve_path "$CUSTOM_BLENDER_PATH")" || die "Custom Blender path does not exist: $CUSTOM_BLENDER_PATH"

        if [[ -d "$custom_path" ]]; then
            BLENDER_INSTALL_DIR="$custom_path"
            warn "Preferred Blender archive was not found. Using the user-provided Blender directory: $BLENDER_INSTALL_DIR"
            return 0
        fi

        if [[ -f "$custom_path" ]]; then
            is_valid_tar_archive "$custom_path" || die "Custom Blender archive is invalid or corrupted: $custom_path"
            warn "Preferred Blender archive was not found. Using the user-provided Blender archive: $custom_path"
            extract_blender_archive "$custom_path"
            return 0
        fi
    fi

    warn "Preferred Blender archive $PREFERRED_BLENDER_ARCHIVE was not found and no custom Blender path was supplied."
    warn "Downloading Blender 5.1.1 as a fallback. Incompatibilities may arise."

    if [[ -f "$fallback_archive_path" ]] && ! is_valid_tar_archive "$fallback_archive_path"; then
        warn "Existing fallback Blender archive is invalid. Downloading a fresh copy from Blender's direct file host."
    fi

    if [[ ! -f "$fallback_archive_path" ]] || ! is_valid_tar_archive "$fallback_archive_path"; then
        log "Downloading fallback Blender archive to $fallback_archive_path."
        download_blender_archive "$FALLBACK_BLENDER_URL" "$fallback_archive_path"
        log "Extracting the downloaded fallback Blender archive."
        extract_blender_archive "$fallback_archive_path"
        return 0
    else
        log "Using existing fallback Blender archive $fallback_archive_path."
    fi

    extract_blender_archive "$fallback_archive_path"
}

verify_pytorch() {
    local output

    log "Verifying that PyTorch, torchvision, and torchaudio import correctly."
    if ! output="$(
        python - <<'PY' 2>&1
import importlib

for package_name in ("torch", "torchvision", "torchaudio"):
    module = importlib.import_module(package_name)
    version = getattr(module, "__version__", "")
    if not version:
        raise SystemExit(f"{package_name} imported but has an empty __version__")
    print(f"{package_name}=OK version={version}")
PY
    )"; then
        printf '%s\n' "$output" >&2
        die "PyTorch package import verification failed."
    fi
    printf '%s\n' "$output"

    [[ "$output" == *"torch=OK version="* ]] || die "torch import check did not report a valid version."
    [[ "$output" == *"torchvision=OK version="* ]] || die "torchvision import check did not report a valid version."
    [[ "$output" == *"torchaudio=OK version="* ]] || die "torchaudio import check did not report a valid version."

    log "Verifying PyTorch runtime details."
    if ! output="$(
        python - <<'PY' 2>&1
import torch

version = getattr(torch, "__version__", "")
if not version:
    raise SystemExit("torch.__version__ is empty")

cuda_available = torch.cuda.is_available()
device_name = "CPU only"

if cuda_available:
    device_name = torch.cuda.get_device_name(0).strip()
    if not device_name:
        raise SystemExit("CUDA is available but torch.cuda.get_device_name(0) returned an empty string")

print(f"torch_version={version}")
print(f"cuda_available={'yes' if cuda_available else 'no'}")
print(f"compute_target={device_name}")
PY
    )"; then
        printf '%s\n' "$output" >&2
        die "PyTorch runtime verification failed."
    fi
    printf '%s\n' "$output"

    [[ "$output" == *"torch_version="* ]] || die "PyTorch runtime check did not report a torch version."
    [[ "$output" == *"cuda_available="* ]] || die "PyTorch runtime check did not report CUDA availability."
    [[ "$output" == *"compute_target="* ]] || die "PyTorch runtime check did not report the compute target."
}

configure_blender_binaries() {
    BLENDER_BIN_PATH="$BLENDER_INSTALL_DIR/blender"
    [[ -f "$BLENDER_BIN_PATH" ]] || die "Blender binary not found at $BLENDER_BIN_PATH."

    chmod +x "$BLENDER_BIN_PATH"
    log "Marked $BLENDER_BIN_PATH as executable."

    if [[ -f "$BLENDER_INSTALL_DIR/blender-softwaregl" ]]; then
        chmod +x "$BLENDER_INSTALL_DIR/blender-softwaregl"
        log "Marked $BLENDER_INSTALL_DIR/blender-softwaregl as executable."
    else
        warn "blender-softwaregl was not found in $BLENDER_INSTALL_DIR."
    fi
}

register_conda_environment_vars() {
    log "Registering PROJECT_ROOT and BLENDER_BIN in conda environment $ENV_NAME."
    conda env config vars set -n "$ENV_NAME" \
        PROJECT_ROOT="$PROJECT_ROOT_PATH" \
        BLENDER_BIN="$BLENDER_BIN_PATH"

    log "Reloading $ENV_NAME so the environment variables are available."
    conda deactivate
    conda activate "$ENV_NAME"

    [[ "${PROJECT_ROOT:-}" == "$PROJECT_ROOT_PATH" ]] || die "PROJECT_ROOT was not loaded correctly after activation."
    [[ "${BLENDER_BIN:-}" == "$BLENDER_BIN_PATH" ]] || die "BLENDER_BIN was not loaded correctly after activation."
}

verify_blender() {
    require_output_contains "Checking Blender version from BLENDER_BIN." "Blender " \
        "$BLENDER_BIN" --version

    require_output_contains "Checking Blender in background mode." "Blender " \
        "$BLENDER_BIN" --background --factory-startup --version
}

create_blender_symlink() {
    local symlink_path="$PROJECT_ROOT_PATH/blender-local"

    ln -sf "$BLENDER_BIN_PATH" "$symlink_path"
    log "Created symlink $symlink_path -> $BLENDER_BIN_PATH."
    [[ -L "$symlink_path" ]] || die "Failed to create the blender-local symlink at $symlink_path."
    [[ "$(readlink -f "$symlink_path")" == "$BLENDER_BIN_PATH" ]] || die "blender-local does not resolve to $BLENDER_BIN_PATH."

    require_output_contains "Checking Blender version through blender-local." "Blender " \
        "$symlink_path" --version
    require_output_contains "Checking background Blender through blender-local." "Blender " \
        "$symlink_path" --background --factory-startup --version
}

main() {
    parse_args "$@"

    [[ -f "$PROJECT_ROOT_PATH/environment.yml" ]] || die "environment.yml not found in $PROJECT_ROOT_PATH."
    command -v tar >/dev/null 2>&1 || die "tar is required but not installed."

    ensure_conda
    create_or_update_environment
    select_blender_installation
    configure_blender_binaries
    verify_pytorch
    register_conda_environment_vars
    verify_blender
    create_blender_symlink

    log "Setup completed successfully."
    log "In future shells, run: conda activate $ENV_NAME"
}

main "$@"
