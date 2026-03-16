from __future__ import annotations

import argparse
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[1]
LOCAL_ROOT = ROOT / ".local-system" / "root"
CHROMEDRIVER = LOCAL_ROOT / "usr" / "bin" / "chromedriver"
DEFAULT_BINARY = LOCAL_ROOT / "usr" / "lib" / "chromium" / "chromium"
SCREENSHOT_DIR = ROOT / "artifacts" / "screenshots"
LOG_DIR = ROOT / "artifacts" / "logs"
ACCESS_LOG = LOG_DIR / "page_access.log"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open a benign page and save a screenshot.")
    parser.add_argument("url", help="Target URL to open")
    parser.add_argument("--output", help="Optional explicit screenshot path")
    parser.add_argument("--wait-seconds", type=float, default=2.0, help="Extra wait after load")
    return parser.parse_args()


def make_output_path(url: str, explicit_output: str | None) -> Path:
    if explicit_output:
        return Path(explicit_output).expanduser().resolve()

    parsed = urlparse(url)
    host = parsed.netloc or "page"
    slug = re.sub(r"[^a-zA-Z0-9.-]+", "-", host).strip("-") or "page"
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return (SCREENSHOT_DIR / f"{timestamp}-{slug}.png").resolve()


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.binary_location = os.environ.get("CHROME_BINARY", str(DEFAULT_BINARY))
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--window-size=1440,2200")
    options.add_argument("--user-data-dir=/tmp/selenium-screenshot-profile")

    return webdriver.Chrome(service=Service(str(CHROMEDRIVER)), options=options)


def append_access_log(requested_url: str, final_url: str, title: str, screenshot_path: Path) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    log_line = (
        f"{timestamp}"
        f" requested_url={requested_url}"
        f" final_url={final_url}"
        f" title={title!r}"
        f" screenshot={screenshot_path}\n"
    )
    with open(ACCESS_LOG, "a", encoding="utf-8") as log_file:
        log_file.write(log_line)


def main() -> None:
    args = parse_args()
    output_path = make_output_path(args.url, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    driver = build_driver()
    try:
        driver.get(args.url)
        WebDriverWait(driver, 30).until(
            lambda current_driver: current_driver.execute_script("return document.readyState")
            == "complete"
        )
        if args.wait_seconds > 0:
            sleep(args.wait_seconds)

        driver.save_screenshot(str(output_path))
        append_access_log(args.url, driver.current_url, driver.title, output_path)
        print(f"TITLE {driver.title}")
        print(f"URL {driver.current_url}")
        print(f"SCREENSHOT {output_path}")
        print(f"LOG {ACCESS_LOG}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
