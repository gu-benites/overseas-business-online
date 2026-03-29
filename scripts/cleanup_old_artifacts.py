import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove logs and screenshot artifacts older than the configured retention window."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Retention window in days. Files/directories older than this are removed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be removed.",
    )
    return parser


def _is_older_than(path: Path, cutoff: datetime) -> bool:
    return datetime.fromtimestamp(path.stat().st_mtime) < cutoff


def _remove_file(path: Path, dry_run: bool) -> int:
    if dry_run:
        print(f"DRY-RUN remove file: {path}")
        return 1
    path.unlink(missing_ok=True)
    print(f"Removed file: {path}")
    return 1


def _remove_tree(path: Path, dry_run: bool) -> int:
    if dry_run:
        print(f"DRY-RUN remove directory: {path}")
        return 1
    shutil.rmtree(path, ignore_errors=True)
    print(f"Removed directory: {path}")
    return 1


def _iter_old_paths(base_dir: Path, cutoff: datetime) -> tuple[list[Path], list[Path]]:
    old_dirs: list[Path] = []
    old_files: list[Path] = []

    for path in sorted(base_dir.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not _is_older_than(path, cutoff):
            continue
        if path.is_dir():
            old_dirs.append(path)
        elif path.is_file():
            old_files.append(path)

    return old_dirs, old_files


def main() -> None:
    args = get_arg_parser().parse_args()
    if args.days < 0:
        raise SystemExit("--days must be >= 0")

    cutoff = datetime.now() - timedelta(days=args.days)

    file_roots = [
        ROOT / ".streamlit_logs",
        ROOT / ".streamlit_logs" / "grouped_click_runs",
        ROOT / "logs",
    ]
    screenshot_roots = [
        ROOT / ".run_screenshots",
    ]

    removed_files = 0
    removed_dirs = 0

    for base_dir in file_roots:
        if not base_dir.exists():
            continue
        old_dirs, old_files = _iter_old_paths(base_dir, cutoff)
        for path in old_dirs:
            removed_dirs += _remove_tree(path, args.dry_run)
        for path in old_files:
            if not path.exists() and not args.dry_run:
                continue
            removed_files += _remove_file(path, args.dry_run)

    for base_dir in screenshot_roots:
        if not base_dir.exists():
            continue
        old_dirs, old_files = _iter_old_paths(base_dir, cutoff)
        for path in old_dirs:
            removed_dirs += _remove_tree(path, args.dry_run)
        for path in old_files:
            if not path.exists() and not args.dry_run:
                continue
            removed_files += _remove_file(path, args.dry_run)

    print(
        "Cleanup finished: "
        f"removed_files={removed_files}, removed_dirs={removed_dirs}, "
        f"cutoff={cutoff.isoformat(timespec='seconds')}, dry_run={args.dry_run}"
    )


if __name__ == "__main__":
    main()
