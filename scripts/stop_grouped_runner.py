import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from job_control import (
    clear_grouped_runner_cli_state,
    kill_process_group,
    process_group_members,
    read_grouped_runner_cli_state,
)


def main() -> None:
    state = read_grouped_runner_cli_state()
    if not state:
        print("No grouped runner CLI state file found.")
        return

    pgid = int(state.get("pgid", 0) or 0)
    pid = int(state.get("pid", 0) or 0)
    if not pgid:
        print("Grouped runner CLI state file is missing PGID.")
        clear_grouped_runner_cli_state(expected_pid=pid or None)
        return

    if not process_group_members(pgid):
        print(f"No live process group found for PGID {pgid}. Cleaning stale state.")
        clear_grouped_runner_cli_state(expected_pid=pid or None)
        return

    print(f"Stopping grouped runner CLI process group PGID {pgid} (pid={pid})...")
    kill_process_group(pgid)
    clear_grouped_runner_cli_state(expected_pid=pid or None)
    print("Grouped runner CLI process group stopped.")


if __name__ == "__main__":
    main()
