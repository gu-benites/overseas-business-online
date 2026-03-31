import argparse
import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import traceback
from time import monotonic, sleep

from browser_cleanup import UC_PROFILE_BASE_DIR, cleanup_stale_uc_profiles
from clicklogs_db import ClickLogsDB
from config_reader import config
from groups_db import GroupQueryRecord, GroupRecord, GroupsDB
from job_control import (
    clear_grouped_runner_cli_state,
    should_register_grouped_runner_cli_state,
    write_grouped_runner_cli_state,
)
from logger import logger
from utils import get_proxy_exit_ip


STAT_PATTERN = re.compile(r"^\|\s*(?P<key>[^|]+?)\s*\|\s*(?P<value>[^|]+?)\s*\|$")
JSON_SUMMARY_PREFIX = "JSON_SUMMARY:"
PROJECT_ROOT = Path(__file__).resolve().parent
USER_HOME = Path.home()
UC_PROFILE_MARKER = str(UC_PROFILE_BASE_DIR) + "/"
PROXY_PLUGIN_MARKER = str(PROJECT_ROOT / "proxy_auth_plugin") + "/"
UC_DRIVER_MARKER = str(
    USER_HOME / ".local" / "share" / "undetected_chromedriver" / "undetected_chromedriver"
)
RUN_CLICK_LOG_DIR = str(PROJECT_ROOT / ".streamlit_logs" / "grouped_click_runs")
PROXY_PAYMENT_REQUIRED_MARKER = "402 Payment Required"
PROXY_TUNNEL_FAILED_MARKER = "ERR_TUNNEL_CONNECTION_FAILED"
PROXY_PAYMENT_REQUIRED_POLL_SECONDS = 60


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False, usage="See grouped-runner-next-steps.md")
    parser.add_argument("--dry-run", action="store_true", help="Only log the planned rotation")
    parser.add_argument("--once", action="store_true", help="Run exactly one cycle and exit")
    parser.add_argument("--group-city", help="Run only a specific city group")
    parser.add_argument(
        "--max-concurrent-groups",
        type=int,
        help="Run up to N groups concurrently in each cycle",
    )
    parser.add_argument(
        "--launch-stagger-seconds",
        type=float,
        help="Wait this many seconds between concurrent group launches",
    )
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
                    "Proxy Tunnel Failed": (
                        "Yes" if payload.get("proxy_tunnel_connection_failed") else "No"
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


def _build_command(
    query: str,
    proxy: str,
    city_name: str | None = None,
    rsw_id: str | None = None,
    grouped_cycle_id: str | None = None,
) -> list[str]:
    if getattr(sys, "frozen", False):
        command = [
            sys.executable,
            "--ad-clicker",
            "-q",
            query,
            "-p",
            proxy,
            "--json-summary",
            "--disable-no-clickable-ads-retry",
        ]
    else:
        command = [
        sys.executable,
        "ad_clicker.py",
        "-q",
        query,
        "-p",
        proxy,
        "--json-summary",
        "--disable-no-clickable-ads-retry",
        ]
    if city_name:
        command.extend(["--city-name", city_name])
    if rsw_id is not None:
        command.extend(["--rsw-id", str(rsw_id)])
    if grouped_cycle_id:
        command.extend(["--grouped-cycle-id", grouped_cycle_id])
    return command


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


def _cleanup_stale_uc_profile_dirs() -> None:
    result = cleanup_stale_uc_profiles(max_age_seconds=0)
    if not result["removed_dirs"]:
        logger.debug("UC profile dir cleanup: no stale profile directories found.")
        return

    freed_mb = result["freed_bytes"] / (1024 * 1024)
    logger.info(
        "UC profile dir cleanup: "
        f"removed {result['removed_dirs']} stale profile dir(s), "
        f"freed ~{freed_mb:.1f} MiB."
    )


def _wait_until_proxy_healthy(group: GroupRecord) -> None:
    logger.warning(
        "Proxy returned 402 Payment Required. "
        "Will poll proxy health every "
        f"{PROXY_PAYMENT_REQUIRED_POLL_SECONDS} seconds before freeing the slot: "
        f"city={group.city_name}, rsw_id={group.rsw_id}"
    )

    while True:
        sleep(PROXY_PAYMENT_REQUIRED_POLL_SECONDS)
        exit_ip = get_proxy_exit_ip(group.proxy, max_retries=1, retry_sleep_seconds=1)
        if exit_ip:
            logger.info(
                "Proxy health restored after 402 Payment Required: "
                f"city={group.city_name}, rsw_id={group.rsw_id}, exit_ip={exit_ip}"
            )
            return
        logger.warning(
            "Proxy still unhealthy after 402 Payment Required. "
            f"Will retry in {PROXY_PAYMENT_REQUIRED_POLL_SECONDS} seconds: "
            f"city={group.city_name}, rsw_id={group.rsw_id}"
        )


def _run_group_once(
    db: GroupsDB,
    group: GroupRecord,
    query: GroupQueryRecord,
    grouped_cycle_id: str | None = None,
) -> None:
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
        _build_command(
            query.query_text,
            group.proxy,
            city_name=group.city_name,
            rsw_id=group.rsw_id,
            grouped_cycle_id=grouped_cycle_id,
        ),
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
    proxy_tunnel_failed = stats.get("Proxy Tunnel Failed")
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
            ", proxy_tunnel_connection_failed="
            f"{summary_payload.get('proxy_tunnel_connection_failed')}"
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
        f"google_blocked_after_captcha={google_blocked_after_captcha or '-'}, "
        f"proxy_tunnel_failed={proxy_tunnel_failed or '-'}"
    )

    if (
        PROXY_PAYMENT_REQUIRED_MARKER in output
        or PROXY_TUNNEL_FAILED_MARKER in output
        or (summary_payload and summary_payload.get("proxy_tunnel_connection_failed"))
    ):
        _wait_until_proxy_healthy(group)


def _resolve_max_concurrent_groups(cli_value: int | None) -> int:
    configured = cli_value if cli_value is not None else config.behavior.max_concurrent_groups
    try:
        value = int(configured or 1)
    except (TypeError, ValueError):
        value = 1
    return max(1, value)


def _resolve_concurrent_launch_stagger_seconds(cli_value: float | None) -> float:
    configured = (
        cli_value
        if cli_value is not None
        else config.behavior.concurrent_group_launch_stagger_seconds
    )
    try:
        value = float(configured or 0)
    except (TypeError, ValueError):
        value = 0.0
    return max(0.0, value)


def _create_run_click_log_path() -> str:
    os.makedirs(RUN_CLICK_LOG_DIR, exist_ok=True)
    filename = f"grouped_clicks_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
    return os.path.join(RUN_CLICK_LOG_DIR, filename)


def _append_run_click_log_header(
    *,
    path: str,
    max_concurrent_groups: int,
    launch_stagger_seconds: float,
    max_runtime_minutes: float | None,
    once: bool,
    dry_run: bool,
    group_city: str | None,
) -> None:
    started_at = datetime.now().isoformat(timespec="seconds")
    lines = [
        f"run_started_at={started_at}",
        f"max_concurrent_groups={max_concurrent_groups}",
        f"launch_stagger_seconds={launch_stagger_seconds:.1f}",
        f"max_runtime_minutes={max_runtime_minutes if max_runtime_minutes else '-'}",
        f"once={'yes' if once else 'no'}",
        f"dry_run={'yes' if dry_run else 'no'}",
        f"group_city={group_city or '-'}",
        "",
    ]
    with open(path, "a", encoding="utf-8") as file_obj:
        file_obj.write("\n".join(lines))


def _append_run_click_log_footer(path: str) -> None:
    finished_at = datetime.now().isoformat(timespec="seconds")
    with open(path, "a", encoding="utf-8") as file_obj:
        file_obj.write(f"\nrun_finished_at={finished_at}\n")


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


def _log_cycle_click_summary(grouped_cycle_id: str, run_click_log_path: str | None = None) -> None:
    click_rows = ClickLogsDB().query_clicks_for_cycle(grouped_cycle_id)
    if not click_rows:
        logger.info(f"Cycle click summary [{grouped_cycle_id}]: no successful clicks recorded.")
        return

    logger.info(
        f"Cycle click summary [{grouped_cycle_id}]: {len(click_rows)} successful click(s)."
    )
    appended_lines: list[str] = []
    for city_name, rsw_id, final_url, click_timestamp, query, category, site_url in click_rows:
        logger.info(
            "Cycle click: "
            f"city={city_name or '-'}, rsw_id={rsw_id or '-'}, final_url={final_url}, "
            f"timestamp={click_timestamp}, query={query}"
        )
        appended_lines.append(
            f"{click_timestamp} | city={city_name or '-'} | rsw_id={rsw_id or '-'} | "
            f"query={query} | final_url={final_url}"
        )
    if run_click_log_path and appended_lines:
        with open(run_click_log_path, "a", encoding="utf-8") as file_obj:
            file_obj.write(f"[{grouped_cycle_id}]\n")
            file_obj.write("\n".join(appended_lines))
            file_obj.write("\n\n")


def _run_cycle(
    db: GroupsDB,
    *,
    dry_run: bool,
    group_city: str | None,
    run_click_log_path: str | None,
) -> bool:
    grouped_cycle_id = datetime.now().strftime("cycle_%Y%m%d_%H%M%S_%f")
    planned = (
        _plan_cycle_without_advancing(db, group_city)
        if dry_run
        else _plan_cycle(db, group_city)
    )
    if not planned:
        logger.info("No runnable active groups found.")
        return False

    max_concurrent_groups = _resolve_max_concurrent_groups(None)
    launch_stagger_seconds = _resolve_concurrent_launch_stagger_seconds(None)
    logger.info(
        "Grouped runner concurrency limit: "
        f"{max_concurrent_groups} group(s) per cycle."
    )
    if max_concurrent_groups > 1:
        logger.info(
            "Grouped runner launch stagger: "
            f"{launch_stagger_seconds:.1f} second(s) between concurrent submissions."
        )

    for group, query in planned:
        _log_planned_group(group, query)
    if dry_run:
        return True

    if max_concurrent_groups == 1:
        for group, query in planned:
            _cleanup_orphan_browsers()
            _cleanup_stale_uc_profile_dirs()
            _run_group_once(db, group, query, grouped_cycle_id=grouped_cycle_id)
        _log_cycle_click_summary(grouped_cycle_id, run_click_log_path)
        return True

    futures = []
    with ThreadPoolExecutor(max_workers=max_concurrent_groups) as executor:
        for index, (group, query) in enumerate(planned):
            _cleanup_orphan_browsers()
            _cleanup_stale_uc_profile_dirs()
            futures.append(
                executor.submit(
                    _run_group_once,
                    db,
                    group,
                    query,
                    grouped_cycle_id,
                )
            )
            if index < len(planned) - 1 and launch_stagger_seconds > 0:
                logger.debug(
                    "Waiting before launching next concurrent group: "
                    f"{launch_stagger_seconds:.1f} second(s)."
                )
                sleep(launch_stagger_seconds)
        for future in as_completed(futures):
            future.result()
    _log_cycle_click_summary(grouped_cycle_id, run_click_log_path)
    return True


def main() -> None:
    args = get_arg_parser().parse_args()
    registered_cli_state = False
    cli_state_pid = os.getpid()
    if should_register_grouped_runner_cli_state():
        write_grouped_runner_cli_state()
        registered_cli_state = True
        atexit.register(clear_grouped_runner_cli_state, cli_state_pid)
        logger.info(
            "Grouped runner CLI state registered: "
            f"pid={os.getpid()}, pgid={os.getpgid(0)}"
        )
    db = GroupsDB()
    deadline = None
    resolved_max_concurrent_groups = _resolve_max_concurrent_groups(args.max_concurrent_groups)
    resolved_launch_stagger_seconds = _resolve_concurrent_launch_stagger_seconds(
        args.launch_stagger_seconds
    )
    config.behavior.max_concurrent_groups = resolved_max_concurrent_groups
    config.behavior.concurrent_group_launch_stagger_seconds = resolved_launch_stagger_seconds

    if args.max_runtime_minutes and args.max_runtime_minutes > 0:
        deadline = monotonic() + (args.max_runtime_minutes * 60)
        logger.info(
            "Grouped runner max runtime enabled: "
            f"{args.max_runtime_minutes} minute(s)"
        )
    logger.info(
        "Grouped runner concurrency configured: "
        f"{resolved_max_concurrent_groups} group(s)."
    )
    logger.info(
        "Grouped runner launch stagger configured: "
        f"{resolved_launch_stagger_seconds:.1f} second(s)."
    )
    run_click_log_path = _create_run_click_log_path()
    _append_run_click_log_header(
        path=run_click_log_path,
        max_concurrent_groups=resolved_max_concurrent_groups,
        launch_stagger_seconds=resolved_launch_stagger_seconds,
        max_runtime_minutes=args.max_runtime_minutes,
        once=args.once,
        dry_run=args.dry_run,
        group_city=args.group_city,
    )
    logger.info(f"Grouped runner click log file: {run_click_log_path}")
    atexit.register(_append_run_click_log_footer, run_click_log_path)

    while True:
        if deadline is not None and monotonic() >= deadline:
            logger.info("Grouped runner timer expired. Stopping loop cleanly.")
            return

        _cleanup_orphan_browsers()
        _cleanup_stale_uc_profile_dirs()

        ran_any = _run_cycle(
            db,
            dry_run=args.dry_run,
            group_city=args.group_city,
            run_click_log_path=run_click_log_path,
        )
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
    except KeyboardInterrupt:
        logger.warning("Grouped runner interrupted by user. Stopping cleanly.")
    except Exception as exp:
        logger.error("Exception occurred. See the details in the log file.")
        message = str(exp).split("\n")[0]
        logger.debug(f"Exception: {message}")
        details = traceback.format_tb(exp.__traceback__)
        logger.debug(f"Exception details: \n{''.join(details)}")
