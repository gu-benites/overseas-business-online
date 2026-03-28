import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from time import sleep


ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / ".runtime"
GROUPED_RUNNER_CLI_STATE = RUNTIME_DIR / "run_grouped_ad_clicker_cli.json"


def _list_process_rows() -> list[dict[str, int | str]]:
    output = subprocess.check_output(
        ["ps", "-eo", "pid,pgid,ppid,comm,args"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    rows: list[dict[str, int | str]] = []
    for raw_line in output.splitlines()[1:]:
        parts = raw_line.strip().split(None, 4)
        if len(parts) < 5:
            continue
        pid, pgid, ppid, comm, args = parts
        try:
            rows.append(
                {
                    "pid": int(pid),
                    "pgid": int(pgid),
                    "ppid": int(ppid),
                    "comm": comm,
                    "args": args,
                }
            )
        except ValueError:
            continue
    return rows


def process_group_members(pgid: int) -> list[dict[str, int | str]]:
    return [row for row in _list_process_rows() if int(row["pgid"]) == int(pgid)]


def kill_process_group(pgid: int, timeout_seconds: int = 5) -> None:
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = timeout_seconds
    while deadline > 0:
        if not process_group_members(pgid):
            return
        sleep(1)
        deadline -= 1

    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return


def should_register_grouped_runner_cli_state() -> bool:
    if os.name != "posix":
        return False

    try:
        parent_args = subprocess.check_output(
            ["ps", "-o", "args=", "-p", str(os.getppid())],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        parent_args = ""

    if "streamlit" in parent_args or "streamlit_gui.py" in parent_args:
        return False
    return True


def write_grouped_runner_cli_state(extra: dict[str, object] | None = None) -> Path:
    RUNTIME_DIR.mkdir(exist_ok=True)
    payload: dict[str, object] = {
        "pid": os.getpid(),
        "pgid": os.getpgid(0),
        "argv": sys.argv,
    }
    if extra:
        payload.update(extra)
    GROUPED_RUNNER_CLI_STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return GROUPED_RUNNER_CLI_STATE


def read_grouped_runner_cli_state() -> dict[str, object] | None:
    if not GROUPED_RUNNER_CLI_STATE.exists():
        return None
    try:
        return json.loads(GROUPED_RUNNER_CLI_STATE.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_grouped_runner_cli_state(expected_pid: int | None = None) -> None:
    if not GROUPED_RUNNER_CLI_STATE.exists():
        return
    if expected_pid is not None:
        state = read_grouped_runner_cli_state()
        if not state or int(state.get("pid", -1)) != int(expected_pid):
            return
    GROUPED_RUNNER_CLI_STATE.unlink(missing_ok=True)
