import signal
import random
import shutil
import string
import traceback
import json
from argparse import ArgumentParser
from dataclasses import asdict
from datetime import datetime
from itertools import chain, filterfalse, zip_longest
from pathlib import Path
from time import sleep

import hooks
from browser_cleanup import release_runtime_dir
from clicklogs_db import ClickLogsDB
from config_reader import config
from logger import logger, update_log_formats
from proxy import get_proxies
from search_controller import (
    BrowserClickRecoveryRequired,
    BrowserSessionUnavailableError,
    SearchController,
)
from stats import SearchStats
from utils import (
    get_queries,
    get_random_user_agent_string,
    get_domains,
    take_screenshot,
    generate_click_report,
)
from webdriver import create_webdriver


if config.behavior.telegram_enabled:
    from telegram_notifier import notify_matching_ads, start_bot


__author__ = "Coşkun Deniz <coskun.denize@gmail.com>"


def _cleanup_reserved_runtime_dir(path: str | Path | None) -> None:
    if not path:
        return

    runtime_dir = Path(path)
    try:
        released = release_runtime_dir(runtime_dir)
        if not released:
            logger.warning(
                f"Skipping runtime dir cleanup because another live process owns {runtime_dir}"
            )
            return

        logger.debug(f"Removing '{runtime_dir}' folder...")
        shutil.rmtree(runtime_dir, ignore_errors=True)
    except Exception as exp:
        logger.debug(f"Failed to cleanup runtime dir '{runtime_dir}': {exp}")


def _get_next_query(current_query: str) -> str:
    """Get the next query from query_file, or reuse current query if unavailable."""

    if not config.paths.query_file:
        return current_query

    queries = [query.strip() for query in get_queries() if query.strip()]
    if not queries:
        return current_query

    try:
        current_index = queries.index(current_query)
    except ValueError:
        return queries[0]

    return queries[(current_index + 1) % len(queries)]


def _should_retry_when_no_clickable_ads() -> bool:
    retry_probability = float(config.behavior.no_clickable_ads_retry_probability)
    exit_probability = float(config.behavior.no_clickable_ads_exit_probability)
    total = retry_probability + exit_probability
    if total <= 0:
        return False

    threshold = retry_probability / total
    roll = random.random()
    logger.debug(
        "No-clickable-ads fallback roll: "
        f"roll={roll:.4f}, retry_threshold={threshold:.4f}, "
        f"retry_probability={retry_probability}, exit_probability={exit_probability}"
    )
    return roll < threshold


def get_arg_parser() -> ArgumentParser:
    """Get argument parser

    :rtype: ArgumentParser
    :returns: ArgumentParser object
    """

    arg_parser = ArgumentParser(add_help=False, usage="See README.md file")
    arg_parser.add_argument("-q", "--query", help="Search query")
    arg_parser.add_argument(
        "-p",
        "--proxy",
        help=(
            'Use the given proxy in "ip:port", "username:password@host:port", '
            'or "host:port:username:password" format'
        ),
    )
    arg_parser.add_argument("--id", help="Browser id for multiprocess run")
    arg_parser.add_argument(
        "--enable_telegram", action="store_true", help="Enable telegram notifications"
    )
    arg_parser.add_argument(
        "--report_clicks", action="store_true", help="Get click report for the given date"
    )
    arg_parser.add_argument("--date", help="Give a specific report date in DD-MM-YYYY format")
    arg_parser.add_argument("--excel", action="store_true", help="Write results to an Excel file")
    arg_parser.add_argument(
        "--check_stealth", action="store_true", help="Check stealth for undetection"
    )
    arg_parser.add_argument("-d", "--device_id", help="Android device ID for assigning to browser")
    arg_parser.add_argument("--city-name", help="City context for grouped runner click logs")
    arg_parser.add_argument("--rsw-id", help="RSW ID context for grouped runner click logs")
    arg_parser.add_argument("--grouped-cycle-id", help="Grouped runner cycle id for click log aggregation")
    arg_parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print machine-readable run summary for automation consumers",
    )
    arg_parser.add_argument(
        "--disable-no-clickable-ads-retry",
        action="store_true",
        help="Disable internal retry/next-query fallback when no clickable ads are found",
    )

    return arg_parser


def main():
    """Entry point for the tool"""

    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()

    def _handle_termination(signum, _frame):
        logger.info(f"Received signal {signum}. Shutting down ad clicker.")
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, _handle_termination)

    if args.report_clicks:
        report_date = datetime.now().strftime("%d-%m-%Y") if not args.date else args.date

        clicklogs_db_client = ClickLogsDB()
        click_results = clicklogs_db_client.query_clicks(click_date=report_date)

        border = (
            "+" + "-" * 70 + "+" + "-" * 27 + "+" + "-" * 9 + "+" + "-" * 12 + "+" + "-" * 12 + "+"
        )

        if click_results:
            print(border)
            print(
                f"| {'URL':68s} | {'Query':25s} | {'Clicks':7s} | {'Time':10s} | {'Category':10s} |"
            )
            print(border)

            for result in click_results:
                url, clicks, category, click_time, search_query = result

                if len(url) > 68:
                    url = url[:65] + "..."

                print(
                    f"| {url:68s} | {search_query:25s} | {str(clicks):7s} | {click_time:10s} | {category:10s} |"
                )

                print(border)

            # write results to Excel with name click_report_dd-mm-yyyy.xlsx
            if args.excel:
                generate_click_report(click_results, report_date)

        else:
            logger.info(f"No click result was found for {report_date}!")

        return

    if args.enable_telegram:
        if config.behavior.telegram_enabled:
            start_bot()
            return
        else:
            logger.info("Please set the telegram_enabled option to true in config and try again.")
            return

    if args.id:
        update_log_formats(args.id)

    if args.proxy:
        proxy = args.proxy
    elif config.paths.proxy_file:
        proxies = get_proxies()
        logger.debug(f"Proxies: {proxies}")
        proxy = random.choice(proxies)
    elif config.webdriver.proxy:
        proxy = config.webdriver.proxy
    else:
        proxy = None

    initial_query = args.query.strip() if args.query else None
    if not initial_query:
        if not config.behavior.query:
            logger.error("Fill the query parameter!")
            raise SystemExit()

        initial_query = config.behavior.query

    domains = get_domains()

    user_agent = get_random_user_agent_string()

    plugin_folder_name = "".join(random.choices(string.ascii_lowercase, k=5))
    driver = None
    country_code = None
    search_controller = None
    json_summary_emitted = False
    fallback_summary = None
    browser_restart_limit = max(
        0,
        int(getattr(config.behavior, "browser_unavailable_restart_attempts", 2) or 0),
    )
    browser_restart_count = 0
    pending_click_recovery = None

    try:
        if args.check_stealth:
            driver, country_code = create_webdriver(proxy, user_agent, plugin_folder_name)
            from webdriver import execute_stealth_js_code

            execute_stealth_js_code(driver)

            driver.get("https://bot.sannysoft.com/")
            sleep(5)
            driver.get("https://browserleaks.com/canvas")
            sleep(10)
            driver.get("https://www.browserscan.net/")
            sleep(15)
            driver.get("https://pixelscan.net/bot-check")
            sleep(30)
            return

        current_query = initial_query
        retries_done = 0
        max_retries = max(0, int(config.behavior.no_clickable_ads_max_retries))

        while True:
            if driver is None:
                driver, country_code = create_webdriver(proxy, user_agent, plugin_folder_name)

            try:
                search_controller = SearchController(
                    driver,
                    current_query,
                    country_code,
                    city_name=args.city_name,
                    rsw_id=args.rsw_id,
                    grouped_cycle_id=args.grouped_cycle_id,
                )

                if args.id:
                    search_controller.set_browser_id(args.id)

                if args.device_id:
                    search_controller.assign_android_device(args.device_id)

                if pending_click_recovery is not None:
                    search_controller._stats = pending_click_recovery.stats_snapshot
                    search_controller.recover_interrupted_click(
                        pending_click_recovery.click_url,
                        category=pending_click_recovery.category,
                        is_ad_element=pending_click_recovery.is_ad_element,
                        click_time=pending_click_recovery.click_time,
                        result_position=pending_click_recovery.result_position,
                        result_url=pending_click_recovery.result_url,
                    )
                    pending_click_recovery = None

                    if config.behavior.hooks_enabled:
                        hooks.after_clicks_hook(driver)

                    logger.info(search_controller.stats)
                    if args.json_summary:
                        print(
                            "JSON_SUMMARY:"
                            + json.dumps(asdict(search_controller.stats), ensure_ascii=False),
                            flush=True,
                        )
                        json_summary_emitted = True
                    break

                if config.behavior.hooks_enabled:
                    hooks.before_search_hook(driver)

                ads, non_ad_links, shopping_ads = search_controller.search_for_ads(
                    non_ad_domains=domains
                )

                if config.behavior.hooks_enabled:
                    hooks.after_search_hook(driver)

                clickable_ad_count = len(ads) + len(shopping_ads)
                if clickable_ad_count == 0:
                    logger.info("No clickable ads found in the search results!")

                    if config.behavior.telegram_enabled:
                        notify_matching_ads(current_query, links=None, stats=search_controller.stats)

                    if (
                        not args.disable_no_clickable_ads_retry
                        and retries_done < max_retries
                        and _should_retry_when_no_clickable_ads()
                    ):
                        next_query = (
                            _get_next_query(current_query)
                            if config.paths.query_file
                            else current_query
                        )
                        logger.info(
                            "No-clickable-ads fallback selected retry. "
                            f"Current query='{current_query}', next query='{next_query}'."
                        )
                        current_query = next_query
                        retries_done += 1
                        continue

                    if args.disable_no_clickable_ads_retry:
                        logger.info(
                            "No-clickable-ads retry is disabled for this run. "
                            "Exiting without switching to global query_file."
                        )

                    logger.info("No-clickable-ads fallback selected clean exit.")
                    logger.info(search_controller.stats)
                    break

                logger.debug(f"Selected click order: {config.behavior.click_order}")

                if config.behavior.click_order == 1:
                    all_links = non_ad_links + ads

                elif config.behavior.click_order == 2:
                    all_links = ads + non_ad_links

                elif config.behavior.click_order == 3:
                    if non_ad_links:
                        all_links = [non_ad_links[0]] + [ads[0]] + non_ad_links[1:] + ads[1:]
                    else:
                        logger.debug("Couldn't found non-ads! Continue with ads only.")
                        all_links = ads

                elif config.behavior.click_order == 4:
                    all_links = list(
                        filterfalse(
                            lambda x: not x, chain.from_iterable(zip_longest(non_ad_links, ads))
                        )
                    )
                else:
                    all_links = ads + non_ad_links
                    random.shuffle(all_links)

                logger.info(f"Found {len(ads) + len(shopping_ads)} ads")

                search_controller.click_shopping_ads(shopping_ads)
                search_controller.click_links(all_links)

                if config.behavior.hooks_enabled:
                    hooks.after_clicks_hook(driver)

                if config.behavior.telegram_enabled:
                    notify_matching_ads(
                        current_query,
                        links=ads + shopping_ads,
                        stats=search_controller.stats,
                    )

                logger.info(search_controller.stats)
                if args.json_summary:
                    print(
                        "JSON_SUMMARY:"
                        + json.dumps(asdict(search_controller.stats), ensure_ascii=False),
                        flush=True,
                    )
                    json_summary_emitted = True
                break

            except BrowserClickRecoveryRequired as exp:
                pending_click_recovery = exp
                if browser_restart_count >= browser_restart_limit:
                    raise

                logger.warning(
                    "Browser session disappeared after the click was already dispatched. "
                    "Restarting browser session "
                    f"{browser_restart_count + 1}/{browser_restart_limit} to finish landing handling."
                )
                browser_restart_count += 1

                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

                profile_dir = getattr(driver, "_runtime_profile_dir", None) if driver else None
                _cleanup_reserved_runtime_dir(profile_dir)
                runtime_driver_dir = (
                    getattr(driver, "_runtime_driver_dir", None) if driver else None
                )
                _cleanup_reserved_runtime_dir(runtime_driver_dir)

                if proxy and config.webdriver.auth:
                    plugin_folder = Path.cwd() / "proxy_auth_plugin" / plugin_folder_name
                    _cleanup_reserved_runtime_dir(plugin_folder)

                driver = None
                country_code = None
                search_controller = None
                proxy = exp.active_proxy or proxy
                user_agent = exp.user_agent or user_agent
                plugin_folder_name = "".join(random.choices(string.ascii_lowercase, k=5))
                sleep(1 * config.behavior.wait_factor)
                continue

            except BrowserSessionUnavailableError:
                attempted_clicks = bool(
                    search_controller
                    and (
                        search_controller.stats.ads_clicked
                        or search_controller.stats.non_ads_clicked
                        or search_controller.stats.shopping_ads_clicked
                    )
                )
                if attempted_clicks or browser_restart_count >= browser_restart_limit:
                    raise

                logger.warning(
                    "Browser session disappeared before the run completed. "
                    f"Restarting browser session {browser_restart_count + 1}/{browser_restart_limit}."
                )
                browser_restart_count += 1

                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

                profile_dir = getattr(driver, "_runtime_profile_dir", None) if driver else None
                _cleanup_reserved_runtime_dir(profile_dir)
                runtime_driver_dir = (
                    getattr(driver, "_runtime_driver_dir", None) if driver else None
                )
                _cleanup_reserved_runtime_dir(runtime_driver_dir)

                if proxy and config.webdriver.auth:
                    plugin_folder = Path.cwd() / "proxy_auth_plugin" / plugin_folder_name
                    _cleanup_reserved_runtime_dir(plugin_folder)

                driver = None
                country_code = None
                search_controller = None
                plugin_folder_name = "".join(random.choices(string.ascii_lowercase, k=5))
                user_agent = get_random_user_agent_string()
                sleep(1 * config.behavior.wait_factor)
                continue

    except Exception as exp:
        logger.error("Exception occurred. See the details in the log file.")

        if driver and config.webdriver.ss_on_exception:
            take_screenshot(driver)

        message = str(exp).split("\n")[0]
        logger.debug(f"Exception: {message}")
        details = traceback.format_tb(exp.__traceback__)
        logger.debug(f"Exception details: \n{''.join(details)}")
        proxy_tunnel_connection_failed = "ERR_TUNNEL_CONNECTION_FAILED" in message
        if search_controller:
            search_controller.stats.proxy_tunnel_connection_failed = proxy_tunnel_connection_failed
        else:
            fallback_stats = SearchStats(
                proxy_tunnel_connection_failed=proxy_tunnel_connection_failed
            )
            fallback_summary = asdict(fallback_stats)

        logger.debug(f"Exception cause: {exp.__cause__}") if exp.__cause__ else None

        if config.behavior.hooks_enabled:
            hooks.exception_hook(driver)

    finally:
        if search_controller:
            if args.json_summary and not json_summary_emitted:
                print(
                    "JSON_SUMMARY:"
                    + json.dumps(asdict(search_controller.stats), ensure_ascii=False),
                    flush=True,
                )
                json_summary_emitted = True

            if config.behavior.hooks_enabled:
                hooks.before_browser_close_hook(driver)

            search_controller.end_search()

            if config.behavior.hooks_enabled:
                hooks.after_browser_close_hook(driver)
        elif args.json_summary and fallback_summary and not json_summary_emitted:
            print(
                "JSON_SUMMARY:" + json.dumps(fallback_summary, ensure_ascii=False),
                flush=True,
            )
            json_summary_emitted = True
        elif driver:
            driver.quit()

        profile_dir = getattr(driver, "_runtime_profile_dir", None) if driver else None
        _cleanup_reserved_runtime_dir(profile_dir)
        runtime_driver_dir = getattr(driver, "_runtime_driver_dir", None) if driver else None
        _cleanup_reserved_runtime_dir(runtime_driver_dir)

        if proxy and config.webdriver.auth:
            plugin_folder = Path.cwd() / "proxy_auth_plugin" / plugin_folder_name
            _cleanup_reserved_runtime_dir(plugin_folder)


if __name__ == "__main__":
    main()
