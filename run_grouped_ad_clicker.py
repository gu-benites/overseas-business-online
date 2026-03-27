import argparse
import json
import os
import re
import signal
import subprocess
import sys
import traceback
from time import monotonic, sleep

from config_reader import config
from groups_db import GroupQueryRecord, GroupRecord, GroupsDB
from logger import logger


STAT_PATTERN = re.compile(r"^\|\s*(?P<key>[^|]+?)\s*\|\s*(?P<value>[^|]+?)\s*\|$")
JSON_SUMMARY_PREFIX = "JSON_SUMMARY:"
UC_PROFILE_MARKER = "/tmp/uc_profiles/"
PROXY_PLUGIN_MARKER = "/home/otavio/overseas-business-online/proxy_auth_plugin/"
UC_DRIVER_MARKER = "/home/otavio/.local/share/undetected_chromedriver/undetected_chromedriver"


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False, usage="See grouped-runner-next-steps.md")
    parser.add_argument("--dry-run", action="store_true", help="Only log the planned rotation")
    parser.add_argument("--once", action="store_true", help="Run exactly one cycle and exit")
    parser.add_argument("--group-city", help="Run only a specific city group")
    parser.add_argument(
        "--max-runtime-minutes",
        type=float,
        help="Stop the continuous loop after the given runtime in minutes",
    )
    return parser


def _parse_ad_clicker_stats(output: str) -> tuple[dict[str, str], dict[str, object] | None]:
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line.startswith(JSON_SUMMARY_PREFIX):
            try:
                payload = json.loads(line[len(JSON_SUMMARY_PREFIX) :])
            except json.JSONDecodeError:
                break
            return (
                {
                    "Initial Proxy IP": str(payload.get("initial_proxy_ip", "") or ""),
                    "Latest Proxy IP": str(payload.get("latest_proxy_ip", "") or ""),
                    "IP Changed Mid-session": (
                        "Yes" if payload.get("ip_changed_mid_session") else "No"
                    ),
                    "Captcha Seen": "Yes" if payload.get("captcha_seen") else "No",
                    "Captcha Token Received": (
                        "Yes" if payload.get("captcha_token_received") else "No"
                    ),
                    "Captcha Token Applied": (
                        "Yes" if payload.get("captcha_token_applied") else "No"
                    ),
                    "Captcha Accepted": "Yes" if payload.get("captcha_accepted") else "No",
                    "Google Blocked After Captcha": (
                        "Yes" if payload.get("google_blocked_after_captcha") else "No"
                    ),
                    "Ads Found": str(payload.get("ads_found", "")),
                    "Ads Clicked": str(payload.get("ads_clicked", "")),
                },
                payload,
            )

    stats: dict[str, str] = {}
    for raw_line in output.splitlines():
        match = STAT_PATTERN.match(raw_line.strip())
        if not match:
            continue
        key = match.group("key").strip()
        value = match.group("value").strip()
        if key:
            stats[key] = value
    return stats, None


def _build_command(query: str, proxy: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--ad-clicker", "-q", query, "-p", proxy, "--json-summary"]
    return [sys.executable, "ad_clicker.py", "-q", query, "-p", proxy, "--json-summary"]


def _log_planned_group(group: GroupRecord, query: GroupQueryRecord) -> None:
    logger.info(
        "Planned group rotation: "
        f"city={group.city_name}, rsw_id={group.rsw_id}, enabled={group.enabled}, "
        f"query_pos={query.position}, query='{query.query_text}'"
    )


def _list_process_rows() -> list[dict[str, object]]:
    output = subprocess.check_output(
        ["ps", "-eo", "pid,ppid,comm,args"],
        text=True,
    )
    rows: list[dict[str, object]] = []
    for raw_line in output.splitlines()[1:]:
        parts = raw_line.strip().split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, comm, args = parts
        try:
            rows.append(
                {
                    "pid": int(pid),
                    "ppid": int(ppid),
                    "comm": comm,
                    "args": args,
                }
            )
        except ValueError:
            continue
    return rows


def _is_ours_browser_process(row: dict[str, object]) -> bool:
    args = str(row["args"])
    comm = str(row["comm"])
    return any(
        marker in args
        for marker in (UC_PROFILE_MARKER, PROXY_PLUGIN_MARKER, UC_DRIVER_MARKER)
    ) or comm.startswith("undetected_chro")


def _collect_tree_pids(
    root_pid: int, children_by_parent: dict[int, list[dict[str, object]]]
) -> set[int]:
    collected: set[int] = set()
    stack = [root_pid]
    while stack:
        current = stack.pop()
        if current in collected:
            continue
        collected.add(current)
        for child in children_by_parent.get(current, []):
            stack.append(int(child["pid"]))
    return collected


def _cleanup_orphan_browsers() -> None:
    rows = _list_process_rows()
    children_by_parent: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        children_by_parent.setdefault(int(row["ppid"]), []).append(row)

    orphan_roots = [
        row
        for row in rows
        if int(row["ppid"]) == 1 and _is_ours_browser_process(row)
    ]
    if not orphan_roots:
        logger.debug("Orphan browser cleanup: no orphan browser trees found.")
        return

    target_pids: set[int] = set()
    for root in orphan_roots:
        target_pids.update(_collect_tree_pids(int(root["pid"]), children_by_parent))

    logger.info(
        "Orphan browser cleanup: "
        f"found {len(orphan_roots)} orphan root(s), terminating {len(target_pids)} process(es)."
    )

    for pid in sorted(target_pids):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except PermissionError:
            logger.warning(f"Orphan browser cleanup: permission denied for pid={pid}")

    sleep(2)

    survivors: list[int] = []
    for pid in sorted(target_pids):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            survivors.append(pid)
        else:
            survivors.append(pid)

    if not survivors:
        logger.info("Orphan browser cleanup: all orphan browser processes were terminated.")
        return

    logger.warning(
        "Orphan browser cleanup: "
        f"{len(survivors)} process(es) still alive after SIGTERM. Sending SIGKILL."
    )
    for pid in survivors:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            continue
        except PermissionError:
            logger.warning(f"Orphan browser cleanup: permission denied for pid={pid}")


def _run_group_once(db: GroupsDB, group: GroupRecord, query: GroupQueryRecord) -> None:
    logger.info(
        "Running group: "
        f"city={group.city_name}, rsw_id={group.rsw_id}, "
        f"query_pos={query.position}, query='{query.query_text}'"
    )

    run_id = db.create_run(
        group.id,
        status="started",
        query_used=query.query_text,
        notes=f"city={group.city_name}, rsw_id={group.rsw_id}",
    )

    result = subprocess.run(
        _build_command(query.query_text, group.proxy),
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    stats, summary_payload = _parse_ad_clicker_stats(output)

    status = "completed" if result.returncode == 0 else "failed"
    if "Exception occurred" in output:
        status = "failed"
    if summary_payload and summary_payload.get("google_blocked_after_captcha"):
        status = "google_blocked_after_captcha"
    if summary_payload and summary_payload.get("ip_changed_mid_session"):
        status = "ip_changed_mid_session"

    initial_proxy_ip = stats.get("Initial Proxy IP")
    latest_proxy_ip = stats.get("Latest Proxy IP")
    ip_changed_mid_session = stats.get("IP Changed Mid-session")
    captcha_seen = stats.get("Captcha Seen")
    captcha_token_received = stats.get("Captcha Token Received")
    captcha_token_applied = stats.get("Captcha Token Applied")
    captcha_accepted = stats.get("Captcha Accepted")
    google_blocked_after_captcha = stats.get("Google Blocked After Captcha")
    ads_found = stats.get("Ads Found")
    ads_clicked = stats.get("Ads Clicked")

    notes = f"city={group.city_name}, rsw_id={group.rsw_id}, returncode={result.returncode}"
    if summary_payload:
        notes += (
            ", initial_proxy_ip="
            f"{summary_payload.get('initial_proxy_ip')}"
            ", latest_proxy_ip="
            f"{summary_payload.get('latest_proxy_ip')}"
            ", ip_changed_mid_session="
            f"{summary_payload.get('ip_changed_mid_session')}"
            ", captcha_token_received="
            f"{summary_payload.get('captcha_token_received')}"
            ", captcha_token_applied="
            f"{summary_payload.get('captcha_token_applied')}"
            ", captcha_accepted="
            f"{summary_payload.get('captcha_accepted')}"
            ", google_blocked_after_captcha="
            f"{summary_payload.get('google_blocked_after_captcha')}"
        )

    db.finish_run(
        run_id,
        status=status,
        query_used=query.query_text,
        captcha_seen=None if captcha_seen is None else captcha_seen.lower() == "yes",
        ads_found=int(ads_found) if ads_found and ads_found.isdigit() else None,
        ads_clicked=int(ads_clicked) if ads_clicked and ads_clicked.isdigit() else None,
        notes=notes,
    )

    logger.info(
        "Group run finished: "
        f"city={group.city_name}, rsw_id={group.rsw_id}, status={status}, "
        f"initial_proxy_ip={initial_proxy_ip or '-'}, "
        f"latest_proxy_ip={latest_proxy_ip or '-'}, "
        f"ip_changed_mid_session={ip_changed_mid_session or '-'}, "
        f"ads_found={ads_found or '-'}, ads_clicked={ads_clicked or '-'}, "
        f"captcha_seen={captcha_seen or '-'}, "
        f"captcha_token_received={captcha_token_received or '-'}, "
        f"captcha_token_applied={captcha_token_applied or '-'}, "
        f"captcha_accepted={captcha_accepted or '-'}, "
        f"google_blocked_after_captcha={google_blocked_after_captcha or '-'}"
    )


def _iter_target_groups(db: GroupsDB, group_city: str | None) -> list[GroupRecord]:
    groups = db.list_groups(enabled_only=True)
    if not group_city:
        return groups
    city_filter = group_city.strip().casefold()
    return [group for group in groups if group.city_name.casefold() == city_filter]


def _plan_cycle(db: GroupsDB, group_city: str | None = None) -> list[tuple[GroupRecord, GroupQueryRecord]]:
    planned: list[tuple[GroupRecord, GroupQueryRecord]] = []
    for group in _iter_target_groups(db, group_city):
        query = db.get_next_query_for_group(group.id)
        if not query:
            logger.warning(
                f"Skipping active group without queries: city={group.city_name}, rsw_id={group.rsw_id}"
            )
            continue
        refreshed_group = db.get_group(group.id)
        if refreshed_group is None:
            continue
        planned.append((refreshed_group, query))
    return planned


def _plan_cycle_without_advancing(
    db: GroupsDB, group_city: str | None = None
) -> list[tuple[GroupRecord, GroupQueryRecord]]:
    planned: list[tuple[GroupRecord, GroupQueryRecord]] = []
    for group in _iter_target_groups(db, group_city):
        query = db.peek_next_query_for_group(group.id)
        if not query:
            logger.warning(
                f"Skipping active group without queries: city={group.city_name}, rsw_id={group.rsw_id}"
            )
            continue
        planned.append((group, query))
    return planned


def _run_cycle(db: GroupsDB, *, dry_run: bool, group_city: str | None) -> bool:
    planned = (
        _plan_cycle_without_advancing(db, group_city)
        if dry_run
        else _plan_cycle(db, group_city)
    )
    if not planned:
        logger.info("No runnable active groups found.")
        return False

    for group, query in planned:
        _log_planned_group(group, query)
        if dry_run:
            continue
        _cleanup_orphan_browsers()
        _run_group_once(db, group, query)
    return True


def main() -> None:
    args = get_arg_parser().parse_args()
    db = GroupsDB()
    deadline = None

    if args.max_runtime_minutes and args.max_runtime_minutes > 0:
        deadline = monotonic() + (args.max_runtime_minutes * 60)
        logger.info(
            "Grouped runner max runtime enabled: "
            f"{args.max_runtime_minutes} minute(s)"
        )

    while True:
        if deadline is not None and monotonic() >= deadline:
            logger.info("Grouped runner timer expired. Stopping loop cleanly.")
            return

        ran_any = _run_cycle(db, dry_run=args.dry_run, group_city=args.group_city)
        if args.once or args.dry_run:
            return

        if deadline is not None and monotonic() >= deadline:
            logger.info("Grouped runner timer expired after cycle completion. Stopping loop cleanly.")
            return

        wait_seconds = config.behavior.loop_wait_time
        if ran_any:
            logger.info(f"Cycle completed. Sleeping {wait_seconds} seconds...")
        else:
            logger.info(f"Sleeping {wait_seconds} seconds...")
        sleep(wait_seconds)


if __name__ == "__main__":
    try:
        main()
    except Exception as exp:
        logger.error("Exception occurred. See the details in the log file.")
        message = str(exp).split("\n")[0]
        logger.debug(f"Exception: {message}")
        details = traceback.format_tb(exp.__traceback__)
        logger.debug(f"Exception details: \n{''.join(details)}")
