from pathlib import Path
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


ROOT = Path(__file__).resolve().parents[1]
LOCAL_ROOT = ROOT / ".local-system" / "root"
CHROMEDRIVER = LOCAL_ROOT / "usr" / "bin" / "chromedriver"
CHROME_BINARY = Path(
    os.environ.get("CHROME_BINARY", LOCAL_ROOT / "usr" / "lib" / "chromium" / "chromium")
)


def main() -> None:
    options = Options()
    options.binary_location = str(CHROME_BINARY)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-data-dir=/tmp/selenium-neutral-profile")

    driver = webdriver.Chrome(service=Service(str(CHROMEDRIVER)), options=options)
    try:
        driver.get("https://example.com")
        title = driver.title
        url = driver.current_url
        print(f"TITLE {title}")
        print(f"URL {url}")

        if "Example Domain" not in title:
            raise SystemExit("Unexpected page title")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
