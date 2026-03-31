import os
import platform
import random
import string
import shutil
import subprocess
import sys
from pathlib import Path
from time import sleep
from typing import Optional, Union

# ---------------------------------------------------------------------------
# Headful display auto-detection
# On the ARM64 VPS the XRDP server exposes Display :10.  When no DISPLAY is
# set (e.g. script launched over plain SSH) we fall back to it so that the
# headful Chromium instance has a valid X server to attach to.
# If Xvfb is preferred instead, start it before the script and export DISPLAY.
# ---------------------------------------------------------------------------
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    os.environ["DISPLAY"] = ":10"

try:
    import requests
    import seleniumbase
    import undetected_chromedriver

except ImportError:
    packages_path = Path.cwd() / "env" / "Lib" / "site-packages"
    sys.path.insert(0, f"{packages_path}")

    import requests
    import seleniumbase
    import undetected_chromedriver

try:
    import pyautogui
except BaseException as exp:
    pyautogui = None
    PYAUTOGUI_IMPORT_ERROR = exp
else:
    PYAUTOGUI_IMPORT_ERROR = None

from config_reader import config
from browser_cleanup import UC_PROFILE_BASE_DIR, cleanup_stale_uc_profiles
from geolocation_db import GeolocationDB
from logger import logger
from proxy import (
    apply_iproyal_sticky_session,
    extract_proxy_session_id,
    install_plugin,
    parse_proxy_value,
)
from utils import get_location, get_locale_language, get_random_sleep


IS_POSIX = sys.platform.startswith(("cygwin", "linux"))
PROJECT_ROOT = Path(__file__).resolve().parent


def _bootstrap_linux_display() -> None:
    """Attach CLI-launched runs to the persistent desktop display when available."""

    if not sys.platform.startswith("linux"):
        return

    x_socket = Path("/tmp/.X11-unix/X10")
    if not os.environ.get("DISPLAY") and x_socket.exists():
        os.environ["DISPLAY"] = ":10"

    if os.environ.get("DISPLAY") == ":10" and not os.environ.get("XAUTHORITY"):
        xauthority_path = Path.home() / ".Xauthority-xvfb-10"
        if xauthority_path.exists():
            os.environ["XAUTHORITY"] = str(xauthority_path)


_bootstrap_linux_display()


def _build_accept_language_header(locale_code: Optional[str]) -> Optional[str]:
    normalized_locale = str(locale_code or "").strip()
    if not normalized_locale:
        return None

    primary_language = normalized_locale.split("-", 1)[0].strip()
    ordered_values: list[str] = []
    for candidate in (normalized_locale, primary_language, "en-US", "en"):
        if candidate and candidate not in ordered_values:
            ordered_values.append(candidate)

    return ",".join(ordered_values)


def _resolve_proxy_locale(country_code: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    locale_code = get_locale_language(country_code)
    normalized_locale = str(locale_code or "").strip()
    if not normalized_locale:
        return None, None

    accept_language = _build_accept_language_header(normalized_locale)
    logger.debug(
        "Resolved proxy locale settings: "
        f"country_code={country_code}, locale={normalized_locale}, "
        f"accept_language={accept_language}"
    )
    return normalized_locale, accept_language


def _apply_browser_locale_overrides(
    driver: Union[undetected_chromedriver.Chrome, seleniumbase.Driver],
    *,
    accept_language: Optional[str],
) -> None:
    if not accept_language:
        return

    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception as exp:
        logger.debug(f"Failed to enable CDP Network domain for locale override: {exp}")

    try:
        driver.execute_cdp_cmd(
            "Network.setExtraHTTPHeaders",
            {"headers": {"Accept-Language": accept_language}},
        )
    except Exception as exp:
        logger.debug(f"Failed to set Accept-Language header override: {exp}")


def _apply_sticky_session_to_proxy(proxy: str, lifetime: str = "30m") -> str:
    """Pin IPRoyal residential proxies to a sticky session for one browser run."""

    return apply_iproyal_sticky_session(proxy, lifetime=lifetime)


def _extract_proxy_session_id(proxy: str) -> Optional[str]:
    return extract_proxy_session_id(proxy)


def _parse_proxy_components(proxy: str) -> tuple[str, str, str, str]:
    """Support both user:pass@host:port and host:port:user:pass formats."""

    parsed = parse_proxy_value(proxy)
    return parsed.username, parsed.password, parsed.host, str(parsed.port)


def _infer_country_code_from_proxy(proxy: str) -> Optional[str]:
    """Infer country code from provider proxy options when IP lookup fails."""

    if not proxy:
        return None

    proxy_lower = proxy.lower()
    for marker in ("_country-", "-country-", "_country_", "-country_"):
        if marker in proxy_lower:
            try:
                suffix = proxy_lower.split(marker, 1)[1]
                candidate = suffix.split("_", 1)[0].split("-", 1)[0]
                if len(candidate) == 2 and candidate.isalpha():
                    return candidate.upper()
            except Exception:
                return None
    return None


def _ensure_seleniumbase_uses_system_chromedriver() -> None:
    """Replace SeleniumBase's local chromedriver with the system ARM binary."""

    try:
        import seleniumbase
    except Exception:
        return

    driver_dir = Path(seleniumbase.__file__).resolve().parent / "drivers"
    local_driver = driver_dir / "chromedriver"
    system_driver = Path("/usr/bin/chromedriver")

    if not system_driver.exists():
        return

    if local_driver.exists():
        try:
            local_driver.unlink()
        except Exception:
            pass

    try:
        local_driver.symlink_to(system_driver)
        logger.debug(f"SeleniumBase chromedriver linked to system driver: {system_driver}")
    except Exception as exp:
        logger.debug(f"Failed to link SeleniumBase chromedriver to system driver: {exp}")


def _require_pyautogui(feature_name: str):
    """Load pyautogui only for features that require a desktop session."""

    if pyautogui is None:
        raise RuntimeError(
            f"{feature_name} requires an active graphical DISPLAY and pyautogui support."
        ) from PYAUTOGUI_IMPORT_ERROR

    return pyautogui


def _get_browser_binary_path() -> str:
    """Find a usable Chrome/Chromium binary for undetected_chromedriver.

    On ARM64 systems (like the Oracle Ampere VPS) the standard Google Chrome
    .deb is not available, so we prioritise ``chromium`` / ``chromium-browser``
    which are shipped by Debian/Ubuntu for aarch64.
    """

    is_arm = platform.machine() in ("aarch64", "arm64", "armv8l")

    if is_arm:
        candidates = [
            os.getenv("CHROME_BINARY"),
            shutil.which("chromium"),
            shutil.which("chromium-browser"),
            "/snap/bin/chromium",
            shutil.which("google-chrome"),
            shutil.which("google-chrome-stable"),
            "/opt/google/chrome/chrome",
        ]
    else:
        candidates = [
            os.getenv("CHROME_BINARY"),
            shutil.which("google-chrome"),
            shutil.which("google-chrome-stable"),
            shutil.which("chromium"),
            shutil.which("chromium-browser"),
            "/opt/google/chrome/chrome",
            "/snap/bin/chromium",
        ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)

    raise RuntimeError(
        "Chrome/Chromium binary not found. Install chromium (ARM64) or "
        "Google Chrome (x86_64), or set the CHROME_BINARY environment variable."
    )


def _resolve_driver_source_executable() -> Path:
    """Resolve a concrete chromedriver binary to copy for this worker.

    We intentionally avoid UC's shared cache so concurrent workers never race
    on ``~/.local/share/undetected_chromedriver``.
    """

    candidates = [
        os.getenv("CHROMEDRIVER"),
        shutil.which("chromedriver"),
        "/usr/bin/chromedriver",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists():
            return candidate_path
    raise RuntimeError(
        "Chromedriver binary not found. Install chromedriver or set CHROMEDRIVER."
    )


def _prepare_isolated_driver_executable() -> str | None:
    """Create a per-run chromedriver copy so concurrent workers never share one binary."""
    source_driver = _resolve_driver_source_executable()
    runtime_driver_dir = PROJECT_ROOT / ".runtime" / "chromedriver_workers"
    runtime_driver_dir.mkdir(parents=True, exist_ok=True)
    isolated_driver = runtime_driver_dir / f"chromedriver-arm64-{os.getpid()}-{random.randint(1000, 9999)}"
    shutil.copy2(source_driver, isolated_driver)
    isolated_driver.chmod(0o755)
    return str(isolated_driver)


def _has_usable_display(display_value: str | None) -> bool:
    if not display_value or not sys.platform.startswith("linux"):
        return False
    try:
        result = subprocess.run(
            ["xdpyinfo", "-display", display_value],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


class CustomChrome(undetected_chromedriver.Chrome):
    """Modified Chrome implementation"""

    def quit(self):

        try:
            # logger.debug("Terminating the browser")
            os.kill(self.browser_pid, 15)
            if IS_POSIX:
                os.waitpid(self.browser_pid, 0)
            else:
                sleep(0.05 * config.behavior.wait_factor)
        except (AttributeError, ChildProcessError, RuntimeError, OSError):
            pass
        except TimeoutError as e:
            logger.debug(e, exc_info=True)
        except Exception:
            pass

        if hasattr(self, "service") and getattr(self.service, "process", None):
            # logger.debug("Stopping webdriver service")
            self.service.stop()

        try:
            if self.reactor:
                # logger.debug("Shutting down Reactor")
                self.reactor.event.set()
        except Exception:
            pass

        if (
            hasattr(self, "keep_user_data_dir")
            and hasattr(self, "user_data_dir")
            and not self.keep_user_data_dir
        ):
            for _ in range(5):
                try:
                    shutil.rmtree(self.user_data_dir, ignore_errors=False)
                except FileNotFoundError:
                    pass
                except (RuntimeError, OSError, PermissionError) as e:
                    logger.debug(
                        "When removing the temp profile, a %s occured: %s\nretrying..."
                        % (e.__class__.__name__, e)
                    )
                else:
                    # logger.debug("successfully removed %s" % self.user_data_dir)
                    break

                sleep(0.1 * config.behavior.wait_factor)

        # dereference patcher, so patcher can start cleaning up as well.
        # this must come last, otherwise it will throw 'in use' errors
        self.patcher = None

        runtime_driver_executable = getattr(self, "_runtime_driver_executable", None)
        if runtime_driver_executable:
            try:
                Path(runtime_driver_executable).unlink(missing_ok=True)
            except Exception:
                pass

    def __del__(self):
        try:
            self.service.process.kill()
        except Exception:  # noqa
            pass

        try:
            self.quit()
        except OSError:
            pass

    @classmethod
    def _ensure_close(cls, self):
        # needs to be a classmethod so finalize can find the reference
        if (
            hasattr(self, "service")
            and hasattr(self.service, "process")
            and hasattr(self.service.process, "kill")
        ):
            self.service.process.kill()

            if IS_POSIX:
                try:
                    # prevent zombie processes
                    os.waitpid(self.service.process.pid, 0)
                except ChildProcessError:
                    pass
                except Exception:
                    pass
            else:
                sleep(0.05 * config.behavior.wait_factor)


def create_webdriver(
    proxy: str, user_agent: Optional[str] = None, plugin_folder_name: Optional[str] = None
) -> tuple[undetected_chromedriver.Chrome, Optional[str]]:
    """Create Selenium Chrome webdriver instance

    :type proxy: str
    :param proxy: Proxy to use in ip:port, user:pass@host:port, or host:port:user:pass format
    :type user_agent: str
    :param user_agent: User agent string
    :type plugin_folder_name: str
    :param plugin_folder_name: Plugin folder name for proxy
    :rtype: tuple
    :returns: (undetected_chromedriver.Chrome, country_code) pair
    """

    if config.webdriver.use_seleniumbase:
        logger.debug("Using SeleniumBase...")
        return create_seleniumbase_driver(proxy, user_agent)

    proxy = _apply_sticky_session_to_proxy(proxy)

    geolocation_db_client = GeolocationDB()
    has_display = _has_usable_display(os.environ.get("DISPLAY"))
    headless_fallback = sys.platform.startswith("linux") and not has_display

    chrome_options = undetected_chromedriver.ChromeOptions()
    chrome_prefs = {
        "webrtc.ip_handling_policy": "disable_non_proxied_udp",
        "webrtc.multiple_routes_enabled": False,
        "webrtc.nonproxied_udp_enabled": False,
    }
    locale_code = None
    accept_language = None
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-service-autorun")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--deny-permission-prompts")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-application-cache")
    chrome_options.add_argument("--disable-breakpad")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-save-password-bubble")
    chrome_options.add_argument("--disable-single-click-autofill")
    chrome_options.add_argument("--disable-prompt-on-repost")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--dns-prefetch-disable")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-search-engine-choice-screen")
    if headless_fallback:
        logger.warning(
            f"No usable X display found for DISPLAY={os.environ.get('DISPLAY')!r}. "
            "Falling back to headless Chrome."
        )
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1366,768")
    if user_agent:
        chrome_options.add_argument(f"--user-agent={user_agent}")

    if IS_POSIX:
        chrome_options.add_argument("--disable-setuid-sandbox")

    disabled_features = [
        "OptimizationGuideModelDownloading",
        "OptimizationHintsFetching",
        "OptimizationTargetPrediction",
        "OptimizationHints",
        "Translate",
        "DownloadBubble",
        "DownloadBubbleV2",
        "PrivacySandboxSettings4",
        "DisableLoadExtensionCommandLineSwitch",
    ]
    chrome_options.add_argument(f"--disable-features={','.join(disabled_features)}")

    if config.webdriver.incognito:
        chrome_options.add_argument("--incognito")

    cleanup_result = cleanup_stale_uc_profiles(max_age_seconds=0)
    if cleanup_result["removed_dirs"]:
        freed_mb = cleanup_result["freed_bytes"] / (1024 * 1024)
        logger.info(
            "UC profile cleanup before browser startup: "
            f"removed {cleanup_result['removed_dirs']} stale profile dir(s), "
            f"freed ~{freed_mb:.1f} MiB."
        )

    base_dir = UC_PROFILE_BASE_DIR
    base_dir.mkdir(exist_ok=True)
    profile_dir = base_dir / f"profile_{random.randint(1000, 9999)}"

    chrome_options.add_argument(f"--user-data-dir={profile_dir}")
    chrome_options.add_argument("--profile-directory=Default")

    country_code = None

    isolated_driver_exe_path = _prepare_isolated_driver_executable()
    driver_exe_path = isolated_driver_exe_path

    browser_binary_path = _get_browser_binary_path()
    if proxy:
        if config.webdriver.auth:
            username, password, host, port = _parse_proxy_components(proxy)

            masked_username = username[:3] + "***" + username[-3:] if len(username) > 6 else "***"
            masked_password = password[:3] + "***" + password[-3:] if len(password) > 6 else "***"
            masked_proxy = f"{masked_username}:{masked_password}@{host}:{port}"

            logger.info(f"Using proxy: {masked_proxy}")
            logger.debug(f"Using proxy: {proxy}")
            session_id = _extract_proxy_session_id(proxy)
            if session_id:
                logger.info(f"Proxy sticky session id: {session_id}")

            install_plugin(chrome_options, host, int(port), username, password, plugin_folder_name)
            sleep(2 * config.behavior.wait_factor)
        else:
            logger.info(f"Using proxy: {proxy}")
            chrome_options.add_argument(f"--proxy-server={proxy}")

        # get location of the proxy IP
        lat, long, country_code, timezone = get_location(geolocation_db_client, proxy)
        if not country_code and getattr(config.webdriver, "identity_mode", "native_linux") == "native_linux":
            inferred_country_code = _infer_country_code_from_proxy(proxy)
            if inferred_country_code:
                country_code = inferred_country_code
                logger.info(
                    "Identity mode 'native_linux' inferred country from proxy options: "
                    f"{country_code}"
                )
        if config.webdriver.language_from_proxy:
            locale_code, accept_language = _resolve_proxy_locale(country_code)
            if accept_language:
                chrome_prefs["intl.accept_languages"] = accept_language
            if locale_code:
                chrome_options.add_argument(f"--lang={locale_code}")

    chrome_options.add_experimental_option("prefs", chrome_prefs)

    driver = CustomChrome(
        browser_executable_path=browser_binary_path,
        driver_executable_path=driver_exe_path,
        options=chrome_options,
        user_multi_procs=False,
        use_subprocess=True,
    )
    driver._runtime_driver_executable = isolated_driver_exe_path

    if locale_code or accept_language:
        _apply_browser_locale_overrides(driver, accept_language=accept_language)

    if proxy:
        accuracy = 95

        # set geolocation and timezone of the browser according to IP address
        if lat and long:
            driver.execute_cdp_cmd(
                "Emulation.setGeolocationOverride",
                {"latitude": lat, "longitude": long, "accuracy": accuracy},
            )

            if not timezone:
                response = requests.get(f"http://timezonefinder.michelfe.it/api/0_{long}_{lat}")

                if response.status_code == 200:
                    timezone = response.json()["tz_name"]

            driver._custom_timezone = timezone

            driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": timezone})

            try:
                timezone_proxy_label = parse_proxy_value(proxy).host_port
            except Exception:
                timezone_proxy_label = proxy
            logger.debug(f"Timezone of {timezone_proxy_label}: {timezone}")
        driver._active_proxy = proxy

    else:
        driver._active_proxy = None

    driver._runtime_profile_dir = profile_dir

    if headless_fallback:
        logger.debug("Skipping window maximize/position because Chrome is running headless.")
    elif config.webdriver.window_size:
        width, height = config.webdriver.window_size.split(",")
        logger.debug(f"Setting window size as {width}x{height} px")
        driver.set_window_size(width, height)
    else:
        logger.debug("Maximizing window...")
        driver.maximize_window()

    if config.webdriver.shift_windows and not headless_fallback:
        width, height = (
            config.webdriver.window_size.split(",")
            if config.webdriver.window_size
            else (None, None)
        )
        _shift_window_position(driver, width, height)

    return (driver, country_code) if config.webdriver.country_domain else (driver, None)


def create_seleniumbase_driver(
    proxy: str, user_agent: Optional[str] = None
) -> tuple[seleniumbase.Driver, Optional[str]]:
    """Create SeleniumBase Chrome webdriver instance

    :type proxy: str
    :param proxy: Proxy to use in ip:port, user:pass@host:port, or host:port:user:pass format
    :type user_agent: str
    :param user_agent: User agent string
    :rtype: tuple
    :returns: (Driver, country_code) pair
    """

    geolocation_db_client = GeolocationDB()
    proxy = _apply_sticky_session_to_proxy(proxy)
    browser_binary_path = _get_browser_binary_path()
    _ensure_seleniumbase_uses_system_chromedriver()
    has_display = _has_usable_display(os.environ.get("DISPLAY"))
    headless_fallback = sys.platform.startswith("linux") and not has_display

    country_code = None
    locale_code = None
    accept_language = None

    if proxy:
        if config.webdriver.auth:
            username, password, host, port = _parse_proxy_components(proxy)

            masked_username = username[:3] + "***" + username[-3:] if len(username) > 6 else "***"
            masked_password = password[:3] + "***" + password[-3:] if len(password) > 6 else "***"
            masked_proxy = f"{masked_username}:{masked_password}@{host}:{port}"

            logger.info(f"Using proxy: {masked_proxy}")
            logger.debug(f"Using proxy: {proxy}")
            session_id = _extract_proxy_session_id(proxy)
            if session_id:
                logger.info(f"Proxy sticky session id: {session_id}")
        else:
            logger.info(f"Using proxy: {proxy}")

        # get location of the proxy IP
        lat, long, country_code, timezone = get_location(geolocation_db_client, proxy)

        if config.webdriver.language_from_proxy:
            locale_code, accept_language = _resolve_proxy_locale(country_code)

    driver = seleniumbase.get_driver(
        browser_name="chrome",
        undetectable=False,
        headless2=headless_fallback,
        do_not_track=True,
        user_agent=user_agent,
        proxy_string=proxy or None,
        multi_proxy=config.behavior.browser_count > 1,
        incognito=config.webdriver.incognito,
        locale_code=locale_code if config.webdriver.language_from_proxy else None,
        binary_location=browser_binary_path,
        no_sandbox=True,
        disable_gpu=True,
    )

    if locale_code or accept_language:
        _apply_browser_locale_overrides(driver, accept_language=accept_language)

    # set geolocation and timezone if available
    if proxy and lat and long:
        accuracy = 95
        try:
            driver.execute_cdp_cmd(
                "Emulation.setGeolocationOverride",
                {"latitude": lat, "longitude": long, "accuracy": accuracy},
            )

            if not timezone:
                response = requests.get(f"http://timezonefinder.michelfe.it/api/0_{long}_{lat}")
                if response.status_code == 200:
                    timezone = response.json()["tz_name"]

            driver._custom_timezone = timezone
            driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": timezone})

            try:
                timezone_proxy_label = parse_proxy_value(proxy).host_port
            except Exception:
                timezone_proxy_label = proxy
            logger.debug(f"Timezone of {timezone_proxy_label}: {timezone}")
        except Exception as exp:
            logger.debug(f"Skipping SeleniumBase CDP geo/timezone override: {exp}")
    driver._active_proxy = proxy if proxy else None

    # handle window size and position
    if headless_fallback:
        logger.warning(
            f"No usable X display found for DISPLAY={os.environ.get('DISPLAY')!r}. "
            "Falling back to headless SeleniumBase Chrome."
        )
        logger.debug("Skipping window maximize/position because SeleniumBase Chrome is headless.")
    elif config.webdriver.window_size:
        width, height = config.webdriver.window_size.split(",")
        logger.debug(f"Setting window size as {width}x{height} px")
        driver.set_window_size(int(width), int(height))
    else:
        logger.debug("Maximizing window...")
        driver.maximize_window()

    if config.webdriver.shift_windows and not headless_fallback:
        width, height = (
            config.webdriver.window_size.split(",")
            if config.webdriver.window_size
            else (None, None)
        )
        _shift_window_position(driver, width, height)

    return (driver, country_code) if config.webdriver.country_domain else (driver, None)


def _shift_window_position(
    driver: Union[undetected_chromedriver.Chrome, seleniumbase.Driver],
    width: int = None,
    height: int = None,
) -> None:
    """Shift the browser window position randomly

    :type driver: Union[undetected_chromedriver.Chrome, seleniumbase.Driver]
    :param driver: WebDriver instance
    :type width: int
    :param width: Predefined window width
    :type height: int
    :param height: Predefined window height
    """

    pyautogui_client = _require_pyautogui("shift_windows")

    # get screen size
    screen_width, screen_height = pyautogui_client.size()

    window_position = driver.get_window_position()
    x, y = window_position["x"], window_position["y"]

    random_x_offset = random.choice(range(150, 300))
    random_y_offset = random.choice(range(75, 150))

    if width and height:
        new_width = int(width) - random_x_offset
        new_height = int(height) - random_y_offset
    else:
        new_width = int(screen_width * 2 / 3) - random_x_offset
        new_height = int(screen_height * 2 / 3) - random_y_offset

    # set the window size and position
    driver.set_window_size(new_width, new_height)

    new_x = min(x + random_x_offset, screen_width - new_width)
    new_y = min(y + random_y_offset, screen_height - new_height)

    logger.debug(f"Setting window position as ({new_x},{new_y})...")

    driver.set_window_position(new_x, new_y)
    sleep(get_random_sleep(0.1, 0.5) * config.behavior.wait_factor)


def _apply_timezone_consistency_script(
    driver: Union[undetected_chromedriver.Chrome, seleniumbase.Driver],
) -> None:
    """Keep timezone JS surfaces aligned with the CDP timezone override."""

    timezone = getattr(driver, "_custom_timezone", None)
    if not timezone:
        return

    driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": timezone})

    timezone_js = f"""
    (() => {{
        const tz = "{timezone}";
        const getOffset = (tzName) => {{
            try {{
                const now = new Date();
                const local = new Date(now.toLocaleString("en-US", {{ timeZone: tzName }}));
                const utc = new Date(now.toLocaleString("en-US", {{ timeZone: "UTC" }}));
                return (utc - local) / 60000; // minutes
            }} catch (e) {{
                return 0;
            }}
        }};
        const offset = getOffset(tz);
        const sign = offset <= 0 ? "+" : "-";
        const absOffset = Math.abs(offset);
        const hours = String(Math.floor(absOffset / 60)).padStart(2, "0");
        const minutes = String(Math.abs(offset) % 60).padStart(2, "0");
        const gmtString = `GMT${{sign}}${{hours}}${{minutes}}`;

        const origIntl = Intl.DateTimeFormat.prototype.resolvedOptions;
        Intl.DateTimeFormat.prototype.resolvedOptions = function() {{
            const opts = origIntl.call(this);
            opts.timeZone = tz;
            return opts;
        }};

        const origOffset = Date.prototype.getTimezoneOffset;
        Date.prototype.getTimezoneOffset = function() {{ return offset; }};

        const origToString = Date.prototype.toString;
        Date.prototype.toString = function() {{
            const str = origToString.call(this);
            return str.replace(/GMT[+-]\\d{{4}}.*$/, `${{gmtString}} (${{tz}})`);
        }};

        const origLocale = Date.prototype.toLocaleString;
        Date.prototype.toLocaleString = function(...args) {{
            const opts = args[1] || {{}};
            if (!opts.timeZone) opts.timeZone = tz;
            return origLocale.call(this, args[0] || undefined, opts);
        }};

        const fakeNative = (n) => `function ${{n}}() {{ [native code] }}`;
        [
            Date.prototype.getTimezoneOffset,
            Date.prototype.toString,
            Date.prototype.toLocaleString,
            Intl.DateTimeFormat.prototype.resolvedOptions
        ].forEach(fn => {{
            if (fn && fn.name)
                Object.defineProperty(fn, "toString", {{ value: () => fakeNative(fn.name) }});
        }});

        Object.defineProperty(Intl, "DateTimeFormat", {{
            value: new Proxy(Intl.DateTimeFormat, {{
                construct(target, args) {{
                    if (args[1] && args[1].timeZone)
                        args[1].timeZone = tz;
                    return new target(...args);
                }}
            }})
        }});
    }})();
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": timezone_js})


def execute_presearch_trust_js_code(
    driver: Union[undetected_chromedriver.Chrome, seleniumbase.Driver],
) -> None:
    """Inject only the minimum consistency patches needed before loading Google."""

    _apply_timezone_consistency_script(driver)
    logger.debug("Applied minimal pre-search trust JavaScript.")


def execute_stealth_js_code(driver: Union[undetected_chromedriver.Chrome, seleniumbase.Driver]):
    """Execute the aggressive post-search stealth JS code for landing-page browsing.

    Signature changes can be tested by loading the following addresses
    - https://browserleaks.com/canvas
    - https://browserleaks.com/webrtc
    - https://browserleaks.com/webgl

    For bot check
    - https://pixelscan.net/bot-check
    - https://www.browserscan.net/
    - https://bot.sannysoft.com/

    :type driver: Union[undetected_chromedriver.Chrome, seleniumbase.Driver]
    :param driver: WebDriver instance
    """

    execute_presearch_trust_js_code(driver)

    # DevTools detection prevention
    devtools_evasion_js = """
    (function() {
        const realInnerWidth = window.innerWidth;
        const realInnerHeight = window.innerHeight;

        // The key: outerHeight should be VERY CLOSE to innerHeight (browser closed)
        // Not random, but consistent small difference
        try {
            Object.defineProperty(window, 'outerHeight', {
                get: function() {
                    return realInnerHeight + 39;
                },
                configurable: true
            });

            Object.defineProperty(window, 'outerWidth', {
                get: function() {
                    return realInnerWidth + 12;
                },
                configurable: true
            });
        } catch(e) {}

        // 2. Override innerWidth/innerHeight to be stable
        try {
            Object.defineProperty(window, 'innerWidth', {
                get: function() {
                    return realInnerWidth;
                },
                configurable: true
            });

            Object.defineProperty(window, 'innerHeight', {
                get: function() {
                    return realInnerHeight;
                },
                configurable: true
            });
        } catch(e) {}

        // 3. Override screen properties
        try {
            Object.defineProperty(screen, 'availWidth', {
                get: () => screen.width,
                configurable: true
            });
            Object.defineProperty(screen, 'availHeight', {
                get: () => screen.height,
                configurable: true
            });
        } catch(e) {}

        // 4. Remove debugger detection
        Object.defineProperty(window, 'devtools', {
            get: () => undefined,
            set: () => {},
            configurable: false
        });

        // 5. Override console methods
        const noop = () => {};
        ['log', 'debug', 'info', 'warn', 'error'].forEach(m => {
            console[m] = noop;
        });

        // 6. Block Function toString inspection
        const OriginalToString = Function.prototype.toString;
        Function.prototype.toString = function() {
            if (this === Function.prototype.toString) {
                return 'function toString() { [native code] }';
            }
            return 'function() { [native code] }';
        };

        // 7. Prevent Error.stack inspection
        const OriginalError = Error;
        window.Error = function(...args) {
            const error = new OriginalError(...args);
            if (error.stack) {
                error.stack = error.stack.split('\\n').slice(0, 2).join('\\n');
            }
            return error;
        };

        // 8. Block debugger statement
        window.eval = new Proxy(window.eval, {
            apply(target, thisArg, args) {
                if (args[0] && args[0].includes('debugger')) {
                    return undefined;
                }
                return Reflect.apply(target, thisArg, args);
            }
        });

    })();
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": devtools_evasion_js})

    # navigator.plugins evasion
    plugins_js = """
    (function() {
        // Save original PluginArray and MimeTypeArray constructors
        const OriginalPluginArray = PluginArray;
        const OriginalMimeTypeArray = MimeTypeArray;

        // Create MimeType objects
        const createMimeType = (type, suffixes, description, plugin) => {
            const mimeType = {
                type: type,
                suffixes: suffixes,
                description: description,
                enabledPlugin: plugin
            };
            return mimeType;
        };

        // Create Plugin objects
        const createPlugin = (name, description, filename, mimeTypes) => {
            const plugin = {
                name: name,
                description: description,
                filename: filename,
                length: mimeTypes.length
            };

            mimeTypes.forEach((mimeType, index) => {
                plugin[index] = createMimeType(
                    mimeType.type,
                    mimeType.suffixes,
                    mimeType.description,
                    plugin
                );
            });

            plugin.item = function(index) {
                return this[index] || null;
            };

            plugin.namedItem = function(name) {
                for (let i = 0; i < this.length; i++) {
                    if (this[i].type === name) return this[i];
                }
                return null;
            };

            return plugin;
        };

        // Create plugin data
        const pluginsData = [
            createPlugin('PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer', [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
            ]),
            createPlugin('Chrome PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer', [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
            ]),
            createPlugin('Chromium PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer', [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
            ]),
            createPlugin('Microsoft Edge PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer', [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
            ]),
            createPlugin('WebKit built-in PDF', 'Portable Document Format', 'internal-pdf-viewer', [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
            ])
        ];

        // Create a real PluginArray instance by extending it
        class FakePluginArray extends OriginalPluginArray {
            constructor(plugins) {
                super();
                plugins.forEach((plugin, index) => {
                    this[index] = plugin;
                    this[plugin.name] = plugin;
                });

                // Override length
                Object.defineProperty(this, 'length', {
                    get: () => plugins.length,
                    enumerable: false
                });
            }

            item(index) {
                return this[index] || null;
            }

            namedItem(name) {
                return this[name] || null;
            }

            refresh() {}
        }

        // Create the plugin array instance
        const pluginArray = new FakePluginArray(pluginsData);

        // Make methods look native
        ['item', 'namedItem', 'refresh'].forEach(method => {
            Object.defineProperty(pluginArray[method], 'toString', {
                value: () => `function ${method}() { [native code] }`,
                writable: false,
                configurable: false
            });
        });

        // Create MimeTypeArray
        class FakeMimeTypeArray extends OriginalMimeTypeArray {
            constructor(plugins) {
                super();
                let mimeIndex = 0;

                plugins.forEach(plugin => {
                    for (let i = 0; i < plugin.length; i++) {
                        this[mimeIndex] = plugin[i];
                        this[plugin[i].type] = plugin[i];
                        mimeIndex++;
                    }
                });

                Object.defineProperty(this, 'length', {
                    get: () => mimeIndex,
                    enumerable: false
                });
            }

            item(index) {
                return this[index] || null;
            }

            namedItem(name) {
                return this[name] || null;
            }
        }

        const mimeTypesArray = new FakeMimeTypeArray(pluginsData);

        // Make methods look native
        ['item', 'namedItem'].forEach(method => {
            Object.defineProperty(mimeTypesArray[method], 'toString', {
                value: () => `function ${method}() { [native code] }`,
                writable: false,
                configurable: false
            });
        });

        // Override navigator.plugins and navigator.mimeTypes
        Object.defineProperty(navigator, 'plugins', {
            get: () => pluginArray,
            enumerable: true,
            configurable: true
        });

        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => mimeTypesArray,
            enumerable: true,
            configurable: true
        });

    })();
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": plugins_js})

    # iframe.contentWindow evasion
    iframe_js = """
    try {
        const defaultGetter = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow').get;
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function() {
                const win = defaultGetter.call(this);
                if (!win) return win;

                try {
                    const proxy = new Proxy(win, {
                        get: (target, prop) => {
                            if (prop === 'self' || prop === 'window' || prop === 'parent' || prop === 'top') {
                                return proxy;
                            }
                            return Reflect.get(target, prop);
                        },
                        has: (target, prop) => {
                            if (prop === 'webdriver') return false;
                            return Reflect.has(target, prop);
                        }
                    });
                    return proxy;
                } catch(e) {
                    return win;
                }
            },
            configurable: true,
            enumerable: true
        });
    } catch(e) {}
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": iframe_js})

    # media codecs evasion
    media_codecs_js = """
    const originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
    HTMLMediaElement.prototype.canPlayType = function(type) {
        if (type === 'video/mp4; codecs="avc1.42E01E"') return 'probably';
        if (type === 'audio/mpeg') return 'probably';
        if (type === 'audio/mp4; codecs="mp4a.40.2"') return 'probably';
        return originalCanPlayType.apply(this, arguments);
    };

    Object.defineProperty(HTMLMediaElement.prototype.canPlayType, 'toString', {
        value: () => 'function canPlayType() { [native code] }'
    });
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": media_codecs_js})

    # canvas fingerprint randomization
    canvas_js = """
    // Generate consistent but random noise seed
    const noiseSeed = Math.random() * 10;

    const noisify = (canvas, context) => {
        const shift = {
            r: Math.floor(noiseSeed * 2) - 1,
            g: Math.floor(noiseSeed * 2) - 1,
            b: Math.floor(noiseSeed * 2) - 1,
            a: Math.floor(noiseSeed * 2) - 1
        };

        const width = canvas.width;
        const height = canvas.height;

        if (width > 0 && height > 0) {
            try {
                const imageData = context.getImageData(0, 0, width, height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i + 0] = imageData.data[i + 0] + shift.r;
                    imageData.data[i + 1] = imageData.data[i + 1] + shift.g;
                    imageData.data[i + 2] = imageData.data[i + 2] + shift.b;
                    imageData.data[i + 3] = imageData.data[i + 3] + shift.a;
                }
                context.putImageData(imageData, 0, 0);
            } catch(e) {}
        }
    };

    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const originalToBlob = HTMLCanvasElement.prototype.toBlob;
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

    HTMLCanvasElement.prototype.toDataURL = function(...args) {
        const context = this.getContext('2d');
        if (context) noisify(this, context);
        return originalToDataURL.apply(this, args);
    };

    HTMLCanvasElement.prototype.toBlob = function(...args) {
        const context = this.getContext('2d');
        if (context) noisify(this, context);
        return originalToBlob.apply(this, args);
    };

    // Protect toString
    Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, 'toString', {
        value: () => 'function toDataURL() { [native code] }'
    });
    Object.defineProperty(HTMLCanvasElement.prototype.toBlob, 'toString', {
        value: () => 'function toBlob() { [native code] }'
    });
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": canvas_js})

    # WebGL vendor/renderer randomization (enhanced)
    webgl_js = """
    // Hardware-based vendor/renderer pairs only (avoid SwiftShader/Google to prevent detection)
    const webglData = [
        { vendor: 'Intel Inc.', renderer: 'ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
        { vendor: 'NVIDIA Corporation', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)' },
        { vendor: 'AMD', renderer: 'ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)' },
        { vendor: 'Intel Inc.', renderer: 'ANGLE (Intel, Intel(R) Iris(TM) Graphics 6100 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
        { vendor: 'NVIDIA Corporation', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)' }
    ];

    const selected = webglData[Math.floor(Math.random() * webglData.length)];
    const vendor = selected.vendor;
    const renderer = selected.renderer;

    // Override getParameter for WebGLRenderingContext
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // Unmasked vendor/renderer
        if (parameter === 37445) return vendor;
        if (parameter === 37446) return renderer;
        // Standard vendor/renderer
        if (parameter === 33901) return vendor;
        if (parameter === 33902) return renderer;
        // Version info
        if (parameter === 7938) return 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
        if (parameter === 35724) return 'WebGL GLSL ES 1.00 (OpenGL ES GLSL ES 1.0 Chromium)';
        // Max texture size
        if (parameter === 3379) return 16384 + Math.floor(Math.random() * 1024);
        // Other parameters
        if (parameter === 34076) return 16;
        if (parameter === 34930) return 16;
        if (parameter === 36349) return 32;
        return getParameter.apply(this, arguments);
    };

    // Same for WebGL2RenderingContext
    if (window.WebGL2RenderingContext) {
        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return vendor;
            if (parameter === 37446) return renderer;
            if (parameter === 33901) return vendor;
            if (parameter === 33902) return renderer;
            if (parameter === 7938) return 'WebGL 2.0 (OpenGL ES 3.0 Chromium)';
            if (parameter === 35724) return 'WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)';
            if (parameter === 3379) return 16384 + Math.floor(Math.random() * 1024);
            if (parameter === 34076) return 16;
            if (parameter === 34930) return 16;
            if (parameter === 36349) return 32;
            return getParameter2.apply(this, arguments);
        };

        Object.defineProperty(WebGL2RenderingContext.prototype.getParameter, 'toString', {
            value: () => 'function getParameter() { [native code] }'
        });
    }

    // Make it look native
    Object.defineProperty(WebGLRenderingContext.prototype.getParameter, 'toString', {
        value: () => 'function getParameter() { [native code] }'
    });
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": webgl_js})

    # WebRTC blocking
    webrtc_js = """
    (function() {
        // 1. Completely disable RTCPeerConnection
        window.RTCPeerConnection = undefined;
        window.webkitRTCPeerConnection = undefined;
        window.mozRTCPeerConnection = undefined;

        // 2. Disable RTCDataChannel
        window.RTCDataChannel = undefined;

        // 3. Block getUserMedia
        if (navigator.mediaDevices) {
            navigator.mediaDevices.getUserMedia = () => Promise.reject(new Error('Permission denied'));
            navigator.mediaDevices.getDisplayMedia = () => Promise.reject(new Error('Permission denied'));
            navigator.mediaDevices.enumerateDevices = () => Promise.resolve([]);
        }

        // 4. Block legacy getUserMedia
        if (navigator.getUserMedia) {
            navigator.getUserMedia = (c, s, e) => e(new Error('Permission denied'));
        }

        // 5. Block webkitGetUserMedia
        if (navigator.webkitGetUserMedia) {
            navigator.webkitGetUserMedia = (c, s, e) => e(new Error('Permission denied'));
        }

        // 6. Disable getStats
        if (window.RTCPeerConnection) {
            window.RTCPeerConnection.prototype.getStats = undefined;
        }

        // 7. Disable createDataChannel
        if (window.RTCPeerConnection) {
            window.RTCPeerConnection.prototype.createDataChannel = undefined;
        }
    })();
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": webrtc_js})

    logger.debug("Applied advanced stealth JavaScript techniques")
