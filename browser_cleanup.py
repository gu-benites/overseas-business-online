import json
import os
import shutil
import subprocess
from hashlib import sha1
from pathlib import Path
from time import time
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parent
UC_PROFILE_BASE_DIR = PROJECT_ROOT / ".tmp_uc_profiles"
LEGACY_TMP_UC_PROFILE_BASE_DIR = Path("/tmp/uc_profiles")
PROXY_AUTH_PLUGIN_BASE_DIR = PROJECT_ROOT / "proxy_auth_plugin"
ISOLATED_CHROMEDRIVER_BASE_DIR = PROJECT_ROOT / ".runtime" / "isolated_chromedrivers"
CITY_PROFILE_BASE_DIR = PROJECT_ROOT / ".runtime" / "city_profiles"
RUNTIME_RESERVATION_DIR = PROJECT_ROOT / ".runtime" / "cleanup_reservations"


def _list_process_args() -> list[str]:
    output = subprocess.check_output(
        ["ps", "-eo", "args"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    return [line.strip() for line in output.splitlines()[1:] if line.strip()]


def _normalize_candidate_path(path: str | Path) -> str:
    return str(Path(path).resolve(strict=False))


def _reservation_file(path: str | Path) -> Path:
    normalized_path = _normalize_candidate_path(path)
    digest = sha1(normalized_path.encode("utf-8")).hexdigest()
    return RUNTIME_RESERVATION_DIR / f"{digest}.json"


def _pid_is_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

    return True


def reserve_runtime_dir(
    path: str | Path,
    *,
    owner_pid: int | None = None,
    metadata: dict[str, object] | None = None,
) -> Path:
    """Reserve a runtime directory before creation so cleanup cannot race it."""

    normalized_path = Path(_normalize_candidate_path(path))
    reservation_path = _reservation_file(normalized_path)
    reservation_path.parent.mkdir(parents=True, exist_ok=True)
    effective_owner_pid = int(owner_pid or os.getpid())

    if reservation_path.exists():
        try:
            with open(reservation_path, "r", encoding="utf-8") as reservation_file:
                existing_payload = json.load(reservation_file)
        except Exception:
            reservation_path.unlink(missing_ok=True)
        else:
            existing_owner_pid = int(existing_payload.get("owner_pid") or 0)
            if (
                existing_owner_pid
                and existing_owner_pid != effective_owner_pid
                and _pid_is_alive(existing_owner_pid)
            ):
                raise RuntimeError(
                    "Runtime directory is already reserved by another live process: "
                    f"{normalized_path}"
                )
            if not _pid_is_alive(existing_owner_pid):
                reservation_path.unlink(missing_ok=True)

    payload = {
        "path": str(normalized_path),
        "owner_pid": effective_owner_pid,
        "reserved_at": int(time()),
        "metadata": metadata or {},
    }

    temp_path = reservation_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as reservation_file:
        json.dump(payload, reservation_file, ensure_ascii=True, sort_keys=True)
    os.replace(temp_path, reservation_path)

    return normalized_path


def reserve_unique_runtime_dir(
    base_dir: str | Path,
    prefix: str,
    *,
    suffix: str = "",
    owner_pid: int | None = None,
    metadata: dict[str, object] | None = None,
    max_attempts: int = 64,
) -> Path:
    """Reserve a unique runtime directory name under a base directory."""

    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    for _ in range(max_attempts):
        candidate = base_path / f"{prefix}{uuid4().hex[:12]}{suffix}"
        try:
            return reserve_runtime_dir(
                candidate,
                owner_pid=owner_pid,
                metadata=metadata,
            )
        except RuntimeError:
            continue

    raise RuntimeError(f"Failed to reserve a unique runtime directory under {base_path}")


def release_runtime_dir(path: str | Path, *, owner_pid: int | None = None) -> bool:
    """Release a reservation previously created by reserve_runtime_dir()."""

    reservation_path = _reservation_file(path)
    if not reservation_path.exists():
        return False

    expected_owner_pid = int(owner_pid or os.getpid())

    try:
        with open(reservation_path, "r", encoding="utf-8") as reservation_file:
            payload = json.load(reservation_file)
    except Exception:
        reservation_path.unlink(missing_ok=True)
        return True

    stored_owner_pid = int(payload.get("owner_pid") or 0)
    if stored_owner_pid and stored_owner_pid != expected_owner_pid and _pid_is_alive(stored_owner_pid):
        return False

    reservation_path.unlink(missing_ok=True)
    return True


def _active_reserved_paths() -> set[str]:
    if not RUNTIME_RESERVATION_DIR.exists():
        return set()

    active_paths: set[str] = set()
    for reservation_path in RUNTIME_RESERVATION_DIR.glob("*.json"):
        try:
            with open(reservation_path, "r", encoding="utf-8") as reservation_file:
                payload = json.load(reservation_file)
        except Exception:
            reservation_path.unlink(missing_ok=True)
            continue

        reserved_path = str(payload.get("path") or "").strip()
        owner_pid = int(payload.get("owner_pid") or 0)
        if not reserved_path:
            reservation_path.unlink(missing_ok=True)
            continue

        if _pid_is_alive(owner_pid):
            active_paths.add(_normalize_candidate_path(reserved_path))
            continue

        reservation_path.unlink(missing_ok=True)

    return active_paths


def list_active_reserved_paths() -> set[str]:
    """Public wrapper for active reserved runtime paths."""

    return _active_reserved_paths()


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
    reserved_paths = _active_reserved_paths()
    removed_dirs = 0
    freed_bytes = 0

    for base_dir in (
        UC_PROFILE_BASE_DIR,
        LEGACY_TMP_UC_PROFILE_BASE_DIR,
        PROXY_AUTH_PLUGIN_BASE_DIR,
        ISOLATED_CHROMEDRIVER_BASE_DIR,
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

            candidate_path = _normalize_candidate_path(candidate)
            if candidate_path in reserved_paths:
                continue

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
