import shutil
import subprocess
from pathlib import Path
from time import time


PROJECT_ROOT = Path(__file__).resolve().parent
UC_PROFILE_BASE_DIR = PROJECT_ROOT / ".tmp_uc_profiles"
LEGACY_TMP_UC_PROFILE_BASE_DIR = Path("/tmp/uc_profiles")
PROXY_AUTH_PLUGIN_BASE_DIR = PROJECT_ROOT / "proxy_auth_plugin"


def _list_process_args() -> list[str]:
    output = subprocess.check_output(
        ["ps", "-eo", "args"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    return [line.strip() for line in output.splitlines()[1:] if line.strip()]


def release_runtime_dir(path: str | Path | None) -> bool:
    """
    Compatibility shim for the older ad_clicker cleanup flow.

    The modern runtime model already uses isolated per-run directories and
    cleans stale ones by checking whether any live process still references the
    path. `ad_clicker.py` still calls `release_runtime_dir()` before deleting a
    profile/driver/plugin directory, so keep that API and align it with the
    current ownership model:

    - return True when the path is absent or no live process references it
    - return False when a live process command line still contains that path
    """

    if not path:
        return True

    runtime_dir = Path(path)
    if not runtime_dir.exists():
        return True

    runtime_dir_str = str(runtime_dir)
    try:
        process_args = _list_process_args()
    except Exception:
        return False

    return not any(runtime_dir_str in args for args in process_args)


def cleanup_stale_uc_profiles(max_age_seconds: int = 1800) -> dict[str, int]:
    """
    Remove old browser runtime directories that are no longer referenced by any process.

    This covers:
    - active UC temp profiles in the project-local directory
    - legacy UC profiles under /tmp
    - generated proxy auth plugin directories

    Returns aggregate counts for logging/inspection.
    """

    now = time()
    process_args = _list_process_args()
    removed_dirs = 0
    freed_bytes = 0

    for base_dir in (
        UC_PROFILE_BASE_DIR,
        LEGACY_TMP_UC_PROFILE_BASE_DIR,
        PROXY_AUTH_PLUGIN_BASE_DIR,
    ):
        if not base_dir.exists():
            continue

        for candidate in base_dir.iterdir():
            if not candidate.is_dir():
                continue
            try:
                age_seconds = now - candidate.stat().st_mtime
            except FileNotFoundError:
                continue
            if age_seconds < max_age_seconds:
                continue

            candidate_path = str(candidate)
            if any(candidate_path in args for args in process_args):
                continue

            size_bytes = 0
            try:
                for child in candidate.rglob("*"):
                    try:
                        if child.is_file():
                            size_bytes += child.stat().st_size
                    except FileNotFoundError:
                        continue
                shutil.rmtree(candidate, ignore_errors=True)
                removed_dirs += 1
                freed_bytes += size_bytes
            except Exception:
                continue

    return {"removed_dirs": removed_dirs, "freed_bytes": freed_bytes}
