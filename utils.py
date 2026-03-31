import json
import platform
import random
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from itertools import cycle
from pathlib import Path
from time import sleep
from typing import Any, Callable, Optional
from urllib.parse import urlparse

try:
    import requests
    import openpyxl
    import undetected_chromedriver
    from openpyxl.styles import Alignment, Font

except ImportError:
    packages_path = Path.cwd() / "env" / "Lib" / "site-packages"
    sys.path.insert(0, f"{packages_path}")

    import requests
    import openpyxl
    import undetected_chromedriver
    from openpyxl.styles import Alignment, Font

from config_reader import config
from geolocation_db import GeolocationDB
from logger import logger
from proxy import get_proxies, parse_proxy_value


class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    BOTH = "BOTH"


def _normalize_user_agent_browser_version(user_agent_string: str) -> str:
    browser_major_version = get_browser_major_version()
    if not browser_major_version or not user_agent_string:
        return user_agent_string

    normalized_user_agent = re.sub(
        r"\b(Chrome|CriOS)/\d+(?:\.\d+){0,3}",
        lambda match: f"{match.group(1)}/{browser_major_version}.0.0.0",
        user_agent_string,
    )

    if normalized_user_agent != user_agent_string:
        logger.debug(
            "Normalized user agent browser version to installed Chrome major: "
            f"{normalized_user_agent}"
        )

    return normalized_user_agent


def get_random_user_agent_string() -> Optional[str]:
    """Get random user agent

    :rtype: Optional[str]
    :returns: User agent string
    """

    identity_mode = getattr(config.webdriver, "identity_mode", "legacy")
    if identity_mode == "native_linux":
        logger.info("Identity mode 'native_linux' enabled. Using browser native Linux desktop identity.")
        return None

    all_user_agents = _get_user_agents(config.paths.user_agents)

    current_os = platform.system()
    filtered_user_agents = []

    if current_os == "Windows":
        filtered_user_agents = [ua for ua in all_user_agents if "Windows" in ua]

    elif current_os == "Darwin":
        filtered_user_agents = [
            ua
            for ua in all_user_agents
            if any(platform in ua for platform in ("Macintosh", "iPhone", "iPad"))
        ]

    elif current_os == "Linux":
        filtered_user_agents = [
            ua
            for ua in all_user_agents
            if "Linux" in ua and "Android" not in ua and "Mobile" not in ua
        ]

    else:
        # fallback to all agents if no matching OS found
        filtered_user_agents = all_user_agents

    if not filtered_user_agents:
        filtered_user_agents = all_user_agents

    user_agent_string = random.choice(filtered_user_agents)
    user_agent_string = _normalize_user_agent_browser_version(user_agent_string)

    logger.debug(f"user_agent: {user_agent_string}")

    return user_agent_string


def get_browser_major_version() -> Optional[int]:
    """Read the installed Chromium/Chrome major version."""

    candidates = (
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        "/usr/bin/chromium",
    )
    for candidate in candidates:
        if not candidate:
            continue
        try:
            output = subprocess.check_output([candidate, "--version"], text=True, timeout=5).strip()
            version_text = output.split()[-1]
            return int(version_text.split(".", 1)[0])
        except Exception:
            continue
    return None


def _get_user_agents(user_agent_file: Path) -> list[str]:
    """Get user agents from file

    :type user_agent_file: Path
    :param user_agent_file: File containing user agents
    :rtype: list
    :returns: List of user agents
    """

    filepath = Path(user_agent_file)

    if not filepath.exists():
        raise SystemExit(f"Couldn't find user agents file: {filepath}")

    with open(filepath, encoding="utf-8") as useragentfile:
        user_agents = [
            user_agent.strip().replace("'", "").replace('"', "")
            for user_agent in useragentfile.read().splitlines()
        ]

    return user_agents


def get_location(geolocation_db_client: GeolocationDB, proxy: str) -> tuple[float, float, str, str]:
    """Get latitude, longitude, country code, and timezone of ip address

    :type geolocation_db_client: GeolocationDB
    :param geolocation_db_client: GeolocationDB instance
    :type proxy: str
    :param proxy: Proxy to get geolocation
    :rtype: tuple
    :returns: (latitude, longitude, country_code, timezone) tuple for the given proxy IP
    """

    try:
        parsed_proxy = parse_proxy_value(proxy)
        proxy_url = parsed_proxy.proxy_url
    except Exception:
        proxy_url = f"http://{proxy}"
        parsed_proxy = None

    proxies_header = {"http": proxy_url, "https": proxy_url}

    ip_address = ""

    if config.webdriver.auth:
        for repeat in range(2):
            try:
                response = requests.get("https://api.ipify.org", proxies=proxies_header, timeout=5)
                ip_address = response.text

                if not ip_address:
                    raise Exception("Failed with https://api.ipify.org")

                break

            except Exception as exp:
                logger.debug(exp)

                try:
                    logger.debug("Trying with ipv4.webshare.io...")
                    response = requests.get(
                        "https://ipv4.webshare.io/", proxies=proxies_header, timeout=5
                    )
                    ip_address = response.text

                    if not ip_address:
                        raise Exception("Failed with https://ipv4.webshare.io")

                    break

                except Exception as exp:
                    logger.debug(exp)

                    try:
                        logger.debug("Trying with ipconfig.io...")
                        response = requests.get(
                            "https://ipconfig.io/json", proxies=proxies_header, timeout=5
                        )
                        ip_address = response.json().get("ip")

                        if not ip_address:
                            raise Exception("Failed with https://ipconfig.io/json")

                        break

                    except Exception as exp:
                        logger.debug(exp)

                        if repeat == 1:
                            break

                        request_retry_timeout = 60 * config.behavior.wait_factor
                        logger.info(f"Request will be resend after {request_retry_timeout} seconds")

                        sleep(request_retry_timeout)

            sleep(get_random_sleep(0.5, 1) * config.behavior.wait_factor)
    else:
        if parsed_proxy:
            ip_address = parsed_proxy.host
        else:
            ip_address = proxy.split(":")[0]

    if not ip_address:
        logger.info(f"Couldn't verify IP address for {proxy}!")
        logger.debug("Geolocation won't be set")
        return (None, None, None, None)

    logger.info(f"Connecting with IP: {ip_address}")

    db_result = geolocation_db_client.query_geolocation(ip_address)

    latitude = None
    longitude = None
    country_code = None
    timezone = None

    if db_result:
        latitude, longitude, country_code = db_result
        logger.debug(f"Cached latitude and longitude for {ip_address}: ({latitude}, {longitude})")
        logger.debug(f"Cached country code for {ip_address}: {country_code}")

        if not country_code:
            try:
                response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=5)
                country_code = response.json().get("country_code")
                timezone = response.json().get("timezone")
                logger.debug(f"Country code for {ip_address}: {country_code}")

            except Exception:
                try:
                    response = requests.get(
                        "https://ifconfig.co/json", proxies=proxies_header, timeout=5
                    )
                    country_code = response.json().get("country_iso")
                    timezone = response.json().get("time_zone")
                except Exception:
                    logger.debug(f"Couldn't find country code for {ip_address}!")

        return (float(latitude), float(longitude), country_code, timezone)

    else:
        retry_count = 0
        max_retry_count = 5
        sleep_seconds = 5 * config.behavior.wait_factor

        while retry_count < max_retry_count:
            try:
                response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=5)
                latitude, longitude, country_code, timezone = (
                    response.json().get("latitude"),
                    response.json().get("longitude"),
                    response.json().get("country_code"),
                    response.json().get("timezone"),
                )

                if not (latitude and longitude and country_code):
                    raise Exception("Failed with https://ipapi.co")

                break
            except Exception as exp:
                logger.debug(exp)
                logger.debug("Continue with ifconfig.co")

                try:
                    response = requests.get(
                        "https://ifconfig.co/json", proxies=proxies_header, timeout=5
                    )
                    latitude, longitude, country_code, timezone = (
                        response.json().get("latitude"),
                        response.json().get("longitude"),
                        response.json().get("country_iso"),
                        response.json().get("time_zone"),
                    )

                    if not (latitude and longitude and country_code):
                        raise Exception("Failed with https://ifconfig.co/json")

                    break
                except Exception as exp:
                    logger.debug(exp)
                    logger.debug("Continue with ipconfig.io")

                    try:
                        response = requests.get(
                            "https://ipconfig.io/json", proxies=proxies_header, timeout=5
                        )
                        latitude, longitude, country_code, timezone = (
                            response.json().get("latitude"),
                            response.json().get("longitude"),
                            response.json().get("country_iso"),
                            response.json().get("time_zone"),
                        )

                        if not (latitude and longitude and country_code):
                            raise Exception("Failed with https://ipconfig.io/json")

                        break
                    except Exception as exp:
                        logger.debug(exp)
                        logger.error(
                            f"Couldn't find latitude and longitude for {ip_address}! "
                            f"Retrying after {sleep_seconds} seconds..."
                        )

                        retry_count += 1
                        sleep(sleep_seconds)
                        sleep_seconds *= 2

            sleep(0.5 * config.behavior.wait_factor)

        if latitude and longitude and country_code:
            logger.debug(f"Latitude and longitude for {ip_address}: ({latitude}, {longitude})")
            logger.debug(f"Country code for {ip_address}: {country_code}")

            geolocation_db_client.save_geolocation(ip_address, latitude, longitude, country_code)

            return (latitude, longitude, country_code, timezone)
        else:
            logger.error(f"Couldn't find latitude, longitude, and country_code for {ip_address}!")
            return (None, None, None, None)


def get_proxy_exit_ip(proxy: str, *, max_retries: int = 1, retry_sleep_seconds: float = 1.5) -> Optional[str]:
    """Resolve the current public exit IP for a proxy using lightweight endpoints."""

    if not proxy:
        return None

    try:
        proxy_url = parse_proxy_value(proxy).proxy_url
    except ValueError:
        proxy_url = f"http://{proxy}"

    proxies_header = {"http": proxy_url, "https": proxy_url}
    endpoints: list[tuple[str, Callable[[requests.Response], Optional[str]]]] = [
        ("https://api.ipify.org", lambda response: response.text.strip()),
        ("https://ipv4.webshare.io/", lambda response: response.text.strip()),
        ("https://ipconfig.io/json", lambda response: response.json().get("ip")),
    ]

    for attempt_index in range(max(1, max_retries)):
        for endpoint, extractor in endpoints:
            try:
                response = requests.get(endpoint, proxies=proxies_header, timeout=5)
                ip_address = extractor(response)
                if ip_address:
                    return str(ip_address).strip()
            except Exception as exp:
                logger.debug(f"Proxy exit IP lookup failed via {endpoint}: {exp}")

        if attempt_index + 1 < max(1, max_retries):
            sleep(retry_sleep_seconds * config.behavior.wait_factor)

    return None


def get_queries() -> list[str]:
    """Get queries from file

    :rtype: list
    :returns: List of queries
    """

    filepath = Path(config.paths.query_file)

    if not filepath.exists():
        raise SystemExit(f"Couldn't find queries file: {filepath}")

    with open(filepath, encoding="utf-8") as queryfile:
        queries = [
            query.strip().replace("'", "").replace('"', "")
            for query in queryfile.read().splitlines()
        ]

    return queries


def get_domains() -> list[str]:
    """Get domains from file

    :rtype: list
    :returns: List of domains
    """

    filepath = Path(config.paths.filtered_domains)

    if not filepath.exists():
        raise SystemExit(f"Couldn't find domains file: {filepath}")

    with open(filepath, encoding="utf-8") as domainsfile:
        domains = [
            domain.strip().replace("'", "").replace('"', "")
            for domain in domainsfile.read().splitlines()
        ]

    logger.debug(f"Domains: {domains}")

    return domains


def get_ad_allowlist_domains() -> list[str]:
    domains = _get_optional_domains(Path(config.paths.ad_allowlist), "Ad allowlist")
    if not domains:
        logger.debug(
            "Ad allowlist mode: disabled "
            "(all domains are eligible except those blocked by the denylist)."
        )
    return domains


def get_ad_denylist_domains() -> list[str]:
    domains = _get_optional_domains(Path(config.paths.ad_denylist), "Ad denylist")
    if domains:
        logger.debug(f"Ad denylist mode: active ({len(domains)} blocked domains).")
    else:
        logger.debug("Ad denylist mode: disabled (no blocked domains configured).")
    return domains


def _get_optional_domains(filepath: Path, label: str) -> list[str]:
    """Read an optional domain list file. Missing file means empty list."""

    if not filepath.exists():
        logger.debug(f"{label} file not found: {filepath}. Continuing with empty list.")
        return []

    with open(filepath, encoding="utf-8") as domainsfile:
        domains = [
            domain.strip().replace("'", "").replace('"', "")
            for domain in domainsfile.read().splitlines()
            if domain.strip() and not domain.strip().startswith("#")
        ]

    logger.debug(f"{label}: {domains}")
    return domains


def domain_matches_url(domain: str, url: str) -> bool:
    """Return True if the given domain matches the URL hostname."""

    if not domain or not url:
        return False

    normalized_domain = domain.lower().strip()
    if normalized_domain.startswith("http://") or normalized_domain.startswith("https://"):
        normalized_domain = urlparse(normalized_domain).netloc.lower()
    normalized_domain = normalized_domain.lstrip(".")

    parsed = urlparse(url)
    hostname = (parsed.netloc or parsed.path or "").lower()
    hostname = hostname.split("@")[-1].split(":")[0]

    return hostname == normalized_domain or hostname.endswith(f".{normalized_domain}")


def add_cookies(driver: undetected_chromedriver.Chrome) -> None:
    """Add cookies from cookies.txt file

    :type driver: undetected_chromedriver.Chrome
    :param driver: Selenium Chrome webdriver instance
    """

    filepath = Path.cwd() / "cookies.txt"

    if not filepath.exists():
        raise SystemExit("Missing cookies.txt file!")

    logger.info(f"Adding cookies from {filepath}")

    with open(filepath, encoding="utf-8") as cookie_file:
        try:
            cookies = json.loads(cookie_file.read())
        except Exception:
            logger.error("Failed to read cookies file. Check format and try again.")
            raise SystemExit()

    for cookie in cookies:
        if cookie["sameSite"] == "strict":
            cookie["sameSite"] = "Strict"
        elif cookie["sameSite"] == "lax":
            cookie["sameSite"] = "Lax"
        else:
            cookie["sameSite"] = "None" if cookie["secure"] else "Lax"

        driver.add_cookie(cookie)


def solve_recaptcha(
    apikey: str,
    sitekey: str,
    current_url: str,
    data_s: str,
    cookies: Optional[str] = None,
    poll_hook: Optional[Callable[[str, int], None]] = None,
    proxy: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[str]:
    """Solve the recaptcha using the 2captcha service

    :type apikey: str
    :param apikey: API key for the 2captcha service
    :type sitekey: str
    :param sitekey: data-sitekey attribute value of the recaptcha element
    :type current_url: str
    :param current_url: Url that is showing the captcha
    :type data_s: str
    :param data_s: data-s attribute of the captcha element
    :type cookies: str
    :param cookies: Cookies to send 2captcha service
    :rtype: str
    :returns: Response code obtained from the service or None
    """

    logger.info("Trying to solve captcha...")
    logger.debug(
        "2captcha target details: "
        f"url={current_url}, sitekey={sitekey}, has_data_s={bool(data_s)}, "
        f"has_cookies={bool(cookies)}, has_user_agent={bool(user_agent)}"
    )

    create_task_url = "https://api.2captcha.com/createTask"
    get_task_result_url = "https://api.2captcha.com/getTaskResult"

    max_retry_count = 13
    create_retry_count = 0
    request_timeout = 30
    max_poll_seconds = max(240, int(240 * config.behavior.wait_factor))
    poll_interval_seconds = max(5, int(5 * config.behavior.wait_factor))
    task_id = None

    base_task: dict[str, Any] = {"websiteURL": current_url, "websiteKey": sitekey}
    if data_s:
        base_task["recaptchaDataSValue"] = data_s
        base_task["enterprisePayload"] = {"s": data_s}
    if cookies:
        normalized_cookies = _normalize_2captcha_cookies(cookies)
        if normalized_cookies:
            base_task["cookies"] = normalized_cookies
    if user_agent:
        base_task["userAgent"] = user_agent

    def _parse_proxy(proxy_value: str) -> Optional[dict[str, Any]]:
        if not proxy_value:
            return None
        try:
            parsed_proxy = parse_proxy_value(proxy_value)
        except ValueError:
            return None
        proxy_config = {
            "proxyType": "http",
            "proxyAddress": parsed_proxy.host,
            "proxyPort": parsed_proxy.port,
        }
        if parsed_proxy.has_auth:
            proxy_config["proxyLogin"] = parsed_proxy.username
            proxy_config["proxyPassword"] = parsed_proxy.password
        return proxy_config

    attempts: list[tuple[str, dict[str, Any]]] = []
    proxy_cfg = _parse_proxy(proxy or "")
    if proxy_cfg:
        # Google Search /sorry/ challenges are currently solving more reliably with
        # standard proxied reCAPTCHA v2 than with the Enterprise task type here.
        # Keep Enterprise behind a flag so it can be re-enabled for comparison later.
        if config.behavior.enable_v2_enterprise_fallback:
            task_v2_enterprise_proxy = dict(base_task)
            task_v2_enterprise_proxy.update({"type": "RecaptchaV2EnterpriseTask", **proxy_cfg})
            attempts.append(("v2_enterprise_with_proxy", task_v2_enterprise_proxy))

        task_v2_proxy = dict(base_task)
        task_v2_proxy.update({"type": "RecaptchaV2Task", **proxy_cfg})
        attempts.append(("v2_with_proxy", task_v2_proxy))

    def _run_attempt(task_label: str, task_data: dict[str, Any]) -> Optional[str]:
        nonlocal create_retry_count, task_id
        create_retry_count = 0
        task_id = None
        create_payload = {"clientKey": apikey, "task": task_data}
        logger.info(f"Trying 2captcha task mode: {task_label}")
        logger.debug(
            "2captcha task payload summary "
            f"({task_label}): type={task_data.get('type')}, "
            f"url={task_data.get('websiteURL')}, "
            f"sitekey={task_data.get('websiteKey')}, "
            f"has_data_s={bool(task_data.get('recaptchaDataSValue'))}, "
            f"has_proxy={'proxyAddress' in task_data}, "
            f"has_cookies={bool(task_data.get('cookies'))}"
        )

        while create_retry_count < max_retry_count:
            try:
                logger.info(
                    "2captcha createTask started "
                    f"({task_label}) attempt={create_retry_count + 1}/{max_retry_count}"
                )
                response = requests.post(create_task_url, json=create_payload, timeout=request_timeout)
                response_data = response.json()
                logger.debug(f"2captcha createTask response ({task_label}): {response_data}")
            except Exception as exp:
                create_retry_count += 1
                logger.error(
                    "2captcha createTask failed before usable response "
                    f"({task_label}) attempt={create_retry_count}/{max_retry_count}: {exp}"
                )
                sleep(5 * config.behavior.wait_factor)
                continue

            error_to_exit, error_to_continue = _check_2captcha_v2_error(response_data, "createTask")
            if error_to_exit:
                logger.error(f"2captcha createTask exited with unrecoverable error ({task_label}).")
                return None
            if error_to_continue:
                logger.warning(
                    "2captcha createTask returned retryable error "
                    f"({task_label}) attempt={create_retry_count + 1}/{max_retry_count}"
                )
                create_retry_count += 1
                continue

            task_id = response_data.get("taskId")
            if task_id:
                logger.info(f"2captcha createTask succeeded ({task_label}) taskId={task_id}")
                break
            create_retry_count += 1
            logger.warning(
                "2captcha createTask returned no taskId "
                f"({task_label}) attempt={create_retry_count}/{max_retry_count}"
            )
            sleep(5 * config.behavior.wait_factor)

        if not task_id:
            logger.error(f"Failed to create 2captcha task ({task_label}).")
            return None

        sleep(15 * config.behavior.wait_factor)
        poll_payload = {"clientKey": apikey, "taskId": task_id}
        poll_retry_count = 0
        poll_deadline = time.monotonic() + max_poll_seconds
        logger.info(
            f"2captcha getTaskResult polling started ({task_label}) "
            f"taskId={task_id} timeout={max_poll_seconds}s"
        )
        while poll_retry_count < max_retry_count and time.monotonic() < poll_deadline:
            try:
                response = requests.post(
                    get_task_result_url, json=poll_payload, timeout=request_timeout
                )
                response_data = response.json()
                logger.debug(f"2captcha getTaskResult ({task_label}): {response_data}")
            except Exception as exp:
                poll_retry_count += 1
                logger.error(
                    "2captcha getTaskResult failed before usable response "
                    f"({task_label}) taskId={task_id} attempt={poll_retry_count}/{max_retry_count}: {exp}"
                )
                sleep(5 * config.behavior.wait_factor)
                continue

            poll_status = str(response_data.get("status", "")).strip() or "unknown"
            if poll_hook:
                try:
                    poll_hook(f"{task_label}:{poll_status}", poll_retry_count)
                except Exception as exp:
                    logger.debug(f"2captcha poll hook failed: {exp}")

            error_to_exit, error_to_continue = _check_2captcha_v2_error(
                response_data, "getTaskResult"
            )
            if error_to_exit:
                logger.error(
                    f"2captcha getTaskResult exited with unrecoverable error ({task_label}) taskId={task_id}."
                )
                return None
            if error_to_continue:
                logger.warning(
                    "2captcha getTaskResult returned retryable error "
                    f"({task_label}) taskId={task_id} attempt={poll_retry_count + 1}/{max_retry_count}"
                )
                poll_retry_count += 1
                continue
            if poll_status == "processing":
                wait_time = poll_interval_seconds
                logger.info(f"Waiting {wait_time} seconds before checking response again...")
                sleep(wait_time)
                poll_retry_count += 1
                continue
            if poll_status == "ready":
                solution = response_data.get("solution", {})
                token = solution.get("gRecaptchaResponse") or solution.get("token")
                logger.info(
                    f"2captcha getTaskResult returned ready ({task_label}) taskId={task_id} "
                    f"has_token={bool(token)}"
                )
                return str(token) if token else None
            poll_retry_count += 1
            sleep(5 * config.behavior.wait_factor)
        logger.warning(
            f"2captcha task timed out while still processing ({task_label}) "
            f"after about {max_poll_seconds} seconds."
        )
        return None

    for label, task in attempts:
        token = _run_attempt(label, task)
        if token:
            return token

    logger.error("Failed to solve captcha!")
    return None


def take_screenshot(driver: undetected_chromedriver.Chrome) -> None:
    """Save screenshot during exception

    :type driver: undetected_chromedriver.Chrome
    :param driver: Selenium Chrome webdriver instance
    """

    now = datetime.now().strftime("%d-%m-%Y_%H_%M_%S")
    filename = f"exception_ss_{now}.png"

    if driver:
        driver.save_screenshot(filename)
        sleep(get_random_sleep(1, 1.5) * config.behavior.wait_factor)
        logger.info(f"Saved screenshot during exception as {filename}")


def generate_click_report(click_results: list[tuple[str, str, str]], report_date: str) -> None:
    """Update results file with new rows

    :type click_results: list
    :param click_results: List of (site_url, clicks, category, click_time, query) tuples
    :type report_date: str
    :param report_date: Date to query clicks
    """

    click_report_file = Path(f"click_report_{report_date}.xlsx")

    workbook = openpyxl.Workbook()
    sheet = workbook.active

    sheet.row_dimensions[1].height = 20

    # add header
    sheet["A1"] = "URL"
    sheet["B1"] = "Query"
    sheet["C1"] = "Clicks"
    sheet["D1"] = "Time"
    sheet["E1"] = "Category"

    bold_font = Font(bold=True)
    center_align = Alignment(horizontal="center", vertical="center")

    for cell in ("A1", "B1", "C1", "D1", "E1"):
        sheet[cell].font = bold_font
        sheet[cell].alignment = center_align

    # adjust column widths
    sheet.column_dimensions["A"].width = 80
    sheet.column_dimensions["B"].width = 25
    sheet.column_dimensions["C"].width = 15
    sheet.column_dimensions["D"].width = 20
    sheet.column_dimensions["E"].width = 15

    for result in click_results:
        url, click_count, category, click_time, query = result
        sheet.append((url, query, click_count, f"{report_date} {click_time}", category))

    for column_letter in ("B", "C", "D", "E"):
        sheet.column_dimensions[column_letter].alignment = center_align

    workbook.save(click_report_file)

    logger.info(f"Results were written to {click_report_file}")


def get_random_sleep(start: float, end: float) -> float:
    """Generate a random number from the given range

    :type start: float
    :param start: Start value
    :type end: float
    :param end: End value
    :rtype: float
    :returns: Randomly selected number rounded to 2 decimals
    """

    return round(random.uniform(start, end), 2)


def _normalize_2captcha_cookies(cookies: str) -> str:
    """Convert cookie pairs to the format expected by 2captcha v2.

    The project historically used "name:value; ..." while v2 expects "name=value; ...".
    """

    cookie_pairs = []
    for pair in cookies.split(";"):
        item = pair.strip()
        if not item:
            continue
        if "=" in item:
            cookie_pairs.append(item)
        elif ":" in item:
            name, value = item.split(":", 1)
            cookie_pairs.append(f"{name.strip()}={value.strip()}")
        else:
            cookie_pairs.append(item)
    return "; ".join(cookie_pairs)


def _check_2captcha_v2_error(response_data: dict[str, Any], stage: str) -> tuple[bool, bool]:
    """Check error object returned by 2captcha API v2."""

    logger.debug("Checking 2captcha v2 response...")

    error_to_exit, error_to_continue = False, False
    error_wait = 5 * config.behavior.wait_factor

    error_id = int(response_data.get("errorId", 0) or 0)
    if error_id == 0:
        return (False, False)

    error_code = str(response_data.get("errorCode", "")).strip()
    error_desc = str(response_data.get("errorDescription", "")).strip()

    if error_code in {"ERROR_WRONG_USER_KEY", "ERROR_KEY_DOES_NOT_EXIST"}:
        logger.error("Invalid API key. Please check your 2captcha API key.")
        error_to_exit = True

    elif error_code == "ERROR_ZERO_BALANCE":
        logger.error("You don't have funds on your account. Please load your account.")
        error_to_exit = True

    elif error_code == "ERROR_NO_SLOT_AVAILABLE":
        logger.error(
            "No worker slot is available for this captcha right now. Waiting before retry..."
        )
        logger.info(f"Waiting {error_wait} seconds before retrying {stage}...")
        sleep(error_wait)
        error_to_continue = True

    elif error_code in {"ERROR_IP_BLOCKED", "IP_BANNED", "ERROR_ACCOUNT_SUSPENDED"}:
        logger.error("2captcha rejected this client IP/account (blocked or suspended).")
        error_to_exit = True

    elif error_code in {"ERROR_GOOGLEKEY", "ERROR_PAGEURL"}:
        logger.error("Blank or malformed sitekey/page URL for 2captcha task.")
        error_to_exit = True

    elif error_code == "ERROR_CAPTCHA_UNSOLVABLE":
        logger.error("Unable to solve the captcha.")
        error_to_exit = True

    else:
        logger.error(f"2captcha {stage} error: {error_code} ({error_desc})")
        error_to_exit = True

    return (error_to_exit, error_to_continue)


def get_locale_language(country_code: str | None) -> str:
    """Get locale language for the given country code

    :type country_code: str
    :param country_code: Country code for proxy IP
    :rtype: str
    :returns: Locale language for the given country code
    """

    normalized_country_code = str(country_code or "").strip().upper()
    logger.debug(f"Getting locale language for {normalized_country_code or 'default'}...")

    with open("country_to_locale.json", "r") as locales_file:
        locales = json.load(locales_file)

    locale_value = locales.get(normalized_country_code, ["en-US"])
    if isinstance(locale_value, list):
        locale_language = next(
            (str(item).strip() for item in locale_value if str(item).strip()),
            "en-US",
        )
    else:
        locale_language = str(locale_value or "").strip() or "en-US"

    logger.debug(
        f"Locale language code for {normalized_country_code or 'default'}: {locale_language}"
    )

    return locale_language


def resolve_redirect(url: str) -> str:
    """Resolve any redirects and return the final destination URL

    :type url: str
    :param url: Input url to resolve
    :rtype: str
    :returns: Final destination URL
    """

    try:
        response = requests.get(url, allow_redirects=True)
        return response.url

    except requests.RequestException as exp:
        logger.error(f"Error resolving URL redirection: {exp}")
        return url


def _make_boost_request(url: str, proxy: str, user_agent: str) -> None:
    """Make a single GET request for the given url through a random proxy and user agent

    :type url: str
    :param url: Input URL to send request to
    :type proxy: str
    :param proxy: Proxy to use for the request
    :type user_agent: str
    :param user_agent: User agent to use for the request
    """

    headers = {"User-Agent": user_agent}
    try:
        proxy_url = parse_proxy_value(proxy).proxy_url
    except ValueError:
        proxy_url = f"http://{proxy}"
    proxy_config = {"http": proxy_url, "https": proxy_url}

    try:
        response = requests.get(url, headers=headers, proxies=proxy_config, timeout=5)
        try:
            proxy_label = parse_proxy_value(proxy).host_port if proxy else proxy
        except ValueError:
            proxy_label = proxy
        logger.debug(
            f"Boosted [{url}] via [{proxy_label}] "
            f"UA={headers['User-Agent']}, Response code: {response.status_code}"
        )

    except Exception as exp:
        logger.debug(f"Boost request failed for [{url}] via [{proxy}]: {exp}")


def boost_requests(url: str) -> None:
    """Send multiple requests to the given URL

    :type url: str
    :param url: Input URL to send requests to
    """

    logger.debug(f"Sending 10 requests to [{url}]...")

    proxies = get_proxies()
    user_agents = _get_user_agents(config.paths.user_agents)

    random.shuffle(proxies)
    random.shuffle(user_agents)

    proxy = cycle(proxies)
    user_agent = cycle(user_agents)

    with ThreadPoolExecutor(max_workers=10) as executor:
        for _ in range(10):
            executor.submit(_make_boost_request, url, next(proxy), next(user_agent))
