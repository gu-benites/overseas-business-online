import os
import platform
import random
import re
import string
import shutil
import subprocess
import sys
from contextlib import contextmanager
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
    import fcntl
except ImportError:
    fcntl = None

try:
    import pyautogui
except BaseException as exp:
    pyautogui = None
    PYAUTOGUI_IMPORT_ERROR = exp
else:
    PYAUTOGUI_IMPORT_ERROR = None

from config_reader import config
from browser_cleanup import (
    CITY_PROFILE_BASE_DIR,
    ISOLATED_CHROMEDRIVER_BASE_DIR,
    UC_PROFILE_BASE_DIR,
    cleanup_stale_uc_profiles,
    release_runtime_dir,
    reserve_runtime_dir,
    reserve_unique_runtime_dir,
)
from geolocation_db import GeolocationDB
from logger import logger
from profile_state_db import ProfileStateDB, build_profile_key
from proxy import (
    apply_iproyal_sticky_session,
    extract_proxy_session_id,
    install_plugin,
    parse_proxy_value,
)
from utils import (
    get_browser_major_version,
    get_location,
    get_locale_language,
    get_proxy_exit_ip,
    get_random_sleep,
)


IS_POSIX = sys.platform.startswith(("cygwin", "linux"))
PROJECT_ROOT = Path(__file__).resolve().parent
COMMON_NOTEBOOK_WINDOW_SIZES = (
    (1366, 768),
    (1536, 864),
    (1600, 900),
    (1920, 1080),
)
COMMON_NOTEBOOK_WINDOW_WEIGHTS = (45, 25, 20, 10)
UC_DEFAULT_WINDOW_ARGS = {"--window-size=1920,1080", "--start-maximized"}
UC_DRIVER_SEED_LOCK_PATH = PROJECT_ROOT / ".runtime" / "locks" / "uc_driver_seed.lock"


def _bootstrap_linux_display() -> None:
    """Attach to the persistent VPS Xvfb display when available."""

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


def _choose_rotating_window_size(
    display_dimensions: Optional[tuple[int, int]] = None,
) -> tuple[int, int]:
    """Pick a realistic notebook-class window size, favoring lower resolutions."""

    candidate_sizes = list(zip(COMMON_NOTEBOOK_WINDOW_SIZES, COMMON_NOTEBOOK_WINDOW_WEIGHTS))
    if display_dimensions:
        display_width, display_height = display_dimensions
        fitting_sizes = [
            (size, weight)
            for size, weight in candidate_sizes
            if size[0] <= display_width and size[1] <= display_height
        ]
        if fitting_sizes:
            candidate_sizes = fitting_sizes
        else:
            width = max(1024, display_width)
            height = max(600, display_height)
            logger.debug(
                "No rotating notebook size fits the active display. "
                f"Using display dimensions {width}x{height}."
            )
            return width, height

    sizes, weights = zip(*candidate_sizes)
    width, height = random.choices(sizes, weights=weights, k=1)[0]
    logger.debug(f"Selected rotating notebook window size: {width}x{height}")
    return width, height


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
    locale_code: Optional[str],
    accept_language: Optional[str],
    user_agent: Optional[str],
) -> None:
    if not locale_code and not accept_language:
        return

    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception as exp:
        logger.debug(f"Failed to enable CDP Network domain for locale override: {exp}")

    if accept_language:
        try:
            driver.execute_cdp_cmd(
                "Network.setExtraHTTPHeaders",
                {"headers": {"Accept-Language": accept_language}},
            )
        except Exception as exp:
            logger.debug(f"Failed to set Accept-Language header override: {exp}")

    try:
        effective_user_agent = user_agent or driver.execute_script("return navigator.userAgent")
        override_payload = {"userAgent": effective_user_agent}
        if accept_language:
            override_payload["acceptLanguage"] = accept_language
        driver.execute_cdp_cmd("Emulation.setUserAgentOverride", override_payload)
    except Exception as exp:
        logger.debug(f"Failed to apply locale/user-agent override: {exp}")


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


def _prepare_profile_runtime(
    *,
    city_name: Optional[str],
    rsw_id: Optional[str],
    proxy: Optional[str],
) -> dict[str, object]:
    """Resolve either a reusable city profile or a per-run ephemeral profile."""

    cleanup_result = cleanup_stale_uc_profiles(max_age_seconds=0)
    if cleanup_result["removed_dirs"]:
        freed_mb = cleanup_result["freed_bytes"] / (1024 * 1024)
        logger.info(
            "UC profile cleanup before browser startup: "
            f"removed {cleanup_result['removed_dirs']} stale profile dir(s), "
            f"freed ~{freed_mb:.1f} MiB."
        )
    profile_state_db = ProfileStateDB()
    profile_state_db.cleanup_expired_or_recycled_profiles()

    reuse_enabled = bool(getattr(config.webdriver, "profile_reuse_enabled", False))
    reuse_key_mode = str(getattr(config.webdriver, "profile_reuse_key", "city") or "city")
    ttl_minutes = max(1, int(getattr(config.webdriver, "profile_reuse_ttl_minutes", 45) or 45))
    current_proxy_ip = get_proxy_exit_ip(proxy, max_retries=1, retry_sleep_seconds=1) if proxy else None
    current_proxy_session_id = _extract_proxy_session_id(proxy) if proxy else None

    if reuse_enabled and city_name:
        profile_key = build_profile_key(city_name, reuse_key_mode)
        state = profile_state_db.ensure_profile(
            profile_key=profile_key,
            city_name=city_name,
            rsw_id=rsw_id,
            ttl_minutes=ttl_minutes,
        )
        profile_dir = Path(state.profile_dir)
        profile_dir.parent.mkdir(parents=True, exist_ok=True)
        between_run_ip_changed = bool(
            current_proxy_ip and state.last_proxy_ip and current_proxy_ip != state.last_proxy_ip
        )
        seed_required = not profile_dir.exists() or state.last_seeded_at is None
        recycle_pending = state.status == "recycle_pending"

        if recycle_pending and profile_dir.exists():
            shutil.rmtree(profile_dir, ignore_errors=True)
            profile_state_db.reset_profile(profile_key)
            seed_required = True
            between_run_ip_changed = False

        try:
            reserve_runtime_dir(
                profile_dir,
                metadata={
                    "kind": "city_profile",
                    "profile_key": profile_key,
                    "city_name": city_name,
                },
            )
        except RuntimeError:
            logger.warning(
                "Reusable city profile '%s' is already in use by another live process. "
                "Falling back to an ephemeral profile for this run.",
                profile_key,
            )
        else:
            profile_dir.mkdir(parents=True, exist_ok=True)
            return {
                "profile_dir": profile_dir,
                "persistent": True,
                "profile_key": profile_key,
                "profile_state_db": profile_state_db,
                "ttl_minutes": ttl_minutes,
                "current_proxy_ip": current_proxy_ip,
                "current_proxy_session_id": current_proxy_session_id,
                "between_run_ip_changed": between_run_ip_changed,
                "seed_required": seed_required,
                "cleanup_policy": (
                    "city_profile_ip_changed_cleanup"
                    if between_run_ip_changed
                    and bool(getattr(config.webdriver, "profile_soft_cleanup_on_ip_change", True))
                    else "city_profile_soft_cleanup"
                ),
            }

    profile_dir = reserve_unique_runtime_dir(
        UC_PROFILE_BASE_DIR,
        prefix="profile_",
        metadata={"kind": "uc_profile"},
    )
    profile_dir.mkdir(parents=True, exist_ok=True)
    return {
        "profile_dir": profile_dir,
        "persistent": False,
        "profile_key": None,
        "profile_state_db": profile_state_db,
        "ttl_minutes": ttl_minutes,
        "current_proxy_ip": current_proxy_ip,
        "current_proxy_session_id": current_proxy_session_id,
        "between_run_ip_changed": False,
        "seed_required": False,
        "cleanup_policy": "ephemeral",
    }


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


def _ensure_local_uc_driver_cache() -> None:
    """Keep the UC driver cache aligned with the system architecture on ARM hosts."""

    if platform.machine() not in ("aarch64", "arm64", "armv8l"):
        return

    system_driver = Path("/usr/bin/chromedriver")
    if not system_driver.exists():
        return

    local_driver = Path(_get_driver_exe_path()).expanduser()
    local_driver.parent.mkdir(parents=True, exist_ok=True)

    should_refresh = not local_driver.exists()
    if not should_refresh:
        try:
            file_output = subprocess.check_output(
                ["file", str(local_driver)],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            should_refresh = "aarch64" not in file_output.lower()
        except Exception:
            should_refresh = True

    if not should_refresh:
        return

    try:
        shutil.copy2(system_driver, local_driver)
        local_driver.chmod(0o755)
        logger.info(f"Refreshed local UC driver cache from system chromedriver: {local_driver}")
    except Exception as exp:
        logger.warning(f"Failed to refresh local UC driver cache: {exp}")


def _get_preferred_driver_executable_path(multi_procs_enabled: bool) -> str | None:
    """Return a stable driver path, avoiding UC's broken x86 cache on ARM hosts."""

    if platform.machine() in ("aarch64", "arm64", "armv8l"):
        system_driver = Path("/usr/bin/chromedriver")
        local_driver = PROJECT_ROOT / ".runtime" / "chromedriver-arm64"
        if system_driver.exists():
            try:
                local_driver.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(system_driver, local_driver)
                local_driver.chmod(0o755)
                return str(local_driver)
            except Exception as exp:
                logger.warning(f"Failed to prepare ARM chromedriver copy: {exp}")
    if multi_procs_enabled:
        driver_exe_path = _get_driver_exe_path()
        if Path(driver_exe_path).exists():
            return driver_exe_path
    return None


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


def _get_display_dimensions(display_value: str | None) -> Optional[tuple[int, int]]:
    if not _has_usable_display(display_value):
        return None

    try:
        result = subprocess.run(
            ["xdpyinfo", "-display", display_value],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None

    if result.returncode != 0:
        return None

    match = re.search(r"dimensions:\s+(\d+)x(\d+)\s+pixels", result.stdout)
    if not match:
        return None

    width = int(match.group(1))
    height = int(match.group(2))
    logger.debug(f"Detected active display dimensions: {width}x{height}")
    return width, height


@contextmanager
def _uc_seed_lock():
    UC_DRIVER_SEED_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(UC_DRIVER_SEED_LOCK_PATH, "a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _get_chromedriver_major_version(driver_path: Path) -> Optional[int]:
    if not driver_path.exists():
        return None

    try:
        version_output = subprocess.check_output(
            [str(driver_path), "--version"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception as exp:
        logger.debug(f"Failed to read ChromeDriver version from {driver_path}: {exp}")
        return None

    match = re.search(r"ChromeDriver\s+(\d+)\.", version_output)
    if not match:
        return None

    return int(match.group(1))


def _ensure_uc_seed_driver(browser_major_version: Optional[int]) -> Path:
    """Ensure a patched shared UC seed driver exists for per-run isolated copies."""

    system_driver = Path("/usr/bin/chromedriver")
    if system_driver.exists():
        return system_driver

    shared_driver = Path(_get_driver_exe_path()).expanduser()
    existing_major = _get_chromedriver_major_version(shared_driver)
    if (
        shared_driver.exists()
        and (
            browser_major_version is None
            or existing_major is None
            or existing_major == browser_major_version
        )
    ):
        return shared_driver

    with _uc_seed_lock():
        existing_major = _get_chromedriver_major_version(shared_driver)
        if (
            shared_driver.exists()
            and (
                browser_major_version is None
                or existing_major is None
                or existing_major == browser_major_version
            )
        ):
            return shared_driver

        logger.info(
            "Bootstrapping shared UC seed ChromeDriver for later isolated per-run copies: "
            f"target_major={browser_major_version or 'auto'}"
        )
        patcher = undetected_chromedriver.patcher.Patcher(
            version_main=browser_major_version or 0,
            user_multi_procs=False,
        )
        patcher.auto()
        seed_driver = Path(patcher.executable_path).expanduser()
        seed_driver.chmod(0o755)
        return seed_driver


def _prepare_isolated_driver_executable(
    browser_major_version: Optional[int],
) -> tuple[str, Path]:
    """Prepare a reserved ChromeDriver directory and executable for one browser run."""

    seed_driver = _ensure_uc_seed_driver(browser_major_version)
    driver_dir = reserve_unique_runtime_dir(
        ISOLATED_CHROMEDRIVER_BASE_DIR,
        prefix="driver_",
        metadata={
            "kind": "chromedriver_runtime",
            "browser_major_version": browser_major_version,
            "seed_driver": str(seed_driver),
        },
    )
    driver_dir.mkdir(parents=True, exist_ok=True)

    executable_name = seed_driver.name or "chromedriver"
    isolated_driver_path = driver_dir / executable_name
    shutil.copy2(seed_driver, isolated_driver_path)
    isolated_driver_path.chmod(0o755)
    logger.debug(
        "Prepared isolated ChromeDriver copy for this browser run: "
        f"seed={seed_driver}, isolated={isolated_driver_path}"
    )
    return str(isolated_driver_path), driver_dir


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
    proxy: str,
    user_agent: Optional[str] = None,
    plugin_folder_name: Optional[str] = None,
    *,
    city_name: Optional[str] = None,
    rsw_id: Optional[str] = None,
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
    prefer_headless = bool(getattr(config.webdriver, "prefer_headless", False))
    headless_mode = sys.platform.startswith("linux") and (prefer_headless or not has_display)
    display_dimensions = _get_display_dimensions(os.environ.get("DISPLAY")) if has_display else None
    rotating_window_size = (
        None
        if config.webdriver.window_size
        else _choose_rotating_window_size(display_dimensions)
    )
    startup_window_size: Optional[tuple[int, int]] = None
    if config.webdriver.window_size:
        width, height = config.webdriver.window_size.split(",")
        startup_window_size = (int(width), int(height))
    elif rotating_window_size:
        startup_window_size = (int(rotating_window_size[0]), int(rotating_window_size[1]))
    elif display_dimensions:
        startup_window_size = (int(display_dimensions[0]), int(display_dimensions[1]))

    chrome_options = ChromeOptions()
    chrome_options._suppress_uc_default_window_args = True
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
    if headless_mode:
        fallback_width, fallback_height = startup_window_size or (1366, 768)
        if prefer_headless and has_display:
            logger.info(
                "Running Chrome in configured headless mode on this VPS because "
                "headless is currently outperforming headful mode."
            )
        else:
            logger.warning(
                f"No usable X display found for DISPLAY={os.environ.get('DISPLAY')!r}. "
                "Falling back to headless Chrome."
            )
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument(f"--window-size={fallback_width},{fallback_height}")
    elif startup_window_size:
        chrome_options.add_argument(
            f"--window-size={startup_window_size[0]},{startup_window_size[1]}"
        )
        chrome_options.add_argument("--window-position=0,0")
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

    profile_runtime = _prepare_profile_runtime(
        city_name=city_name,
        rsw_id=rsw_id,
        proxy=proxy,
    )
    profile_dir = Path(str(profile_runtime["profile_dir"]))

    chrome_options.add_argument(f"--user-data-dir={profile_dir}")
    chrome_options.add_argument("--profile-directory=Default")

    country_code = None
    driver = None
    runtime_driver_dir = None

    try:
        multi_browser_flag_file = Path(".MULTI_BROWSERS_IN_USE")
        multi_procs_enabled = multi_browser_flag_file.exists()

        browser_binary_path = _get_browser_binary_path()
        browser_major_version = get_browser_major_version()
        if browser_major_version:
            logger.debug(f"Detected browser major version: {browser_major_version}")
        _ensure_local_uc_driver_cache()
        if getattr(config.webdriver, "isolated_chromedriver_per_run", False):
            driver_exe_path, runtime_driver_dir = _prepare_isolated_driver_executable(
                browser_major_version
            )
            multi_procs_enabled = False
        else:
            driver_exe_path = _get_preferred_driver_executable_path(multi_procs_enabled)
        if proxy:
            if config.webdriver.auth:
                username, password, host, port = _parse_proxy_components(proxy)

                masked_username = (
                    username[:3] + "***" + username[-3:] if len(username) > 6 else "***"
                )
                masked_password = (
                    password[:3] + "***" + password[-3:] if len(password) > 6 else "***"
                )
                masked_proxy = f"{masked_username}:{masked_password}@{host}:{port}"

                logger.info(f"Using proxy: {masked_proxy}")
                logger.debug(f"Using proxy: {proxy}")
                session_id = _extract_proxy_session_id(proxy)
                if session_id:
                    logger.info(f"Proxy sticky session id: {session_id}")

                install_plugin(
                    chrome_options,
                    host,
                    int(port),
                    username,
                    password,
                    plugin_folder_name,
                )
                sleep(2 * config.behavior.wait_factor)
            else:
                logger.info(f"Using proxy: {proxy}")
                chrome_options.add_argument(f"--proxy-server={proxy}")

            # get location of the proxy IP
            lat, long, country_code, timezone = get_location(geolocation_db_client, proxy)
            if (
                not country_code
                and getattr(config.webdriver, "identity_mode", "legacy") == "native_linux"
            ):
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
            headless=headless_mode,
            version_main=browser_major_version,
            user_multi_procs=multi_procs_enabled,
            use_subprocess=True,
        )
        driver._active_proxy = proxy if proxy else None
        driver._active_user_agent = user_agent

        if proxy:
            accuracy = 95

            # set geolocation and timezone of the browser according to IP address
            if lat and long:
                driver.execute_cdp_cmd(
                    "Emulation.setGeolocationOverride",
                    {"latitude": lat, "longitude": long, "accuracy": accuracy},
                )

                if not timezone:
                    response = requests.get(
                        f"http://timezonefinder.michelfe.it/api/0_{long}_{lat}"
                    )

                    if response.status_code == 200:
                        timezone = response.json()["tz_name"]

                driver._custom_timezone = timezone

                driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": timezone})

                try:
                    timezone_proxy_label = parse_proxy_value(proxy).host_port
                except Exception:
                    timezone_proxy_label = proxy
                logger.debug(f"Timezone of {timezone_proxy_label}: {timezone}")

        if locale_code or accept_language:
            _apply_browser_locale_overrides(
                driver,
                locale_code=locale_code,
                accept_language=accept_language,
                user_agent=user_agent,
            )

        driver._runtime_profile_dir = str(profile_dir)
        driver._runtime_profile_persistent = bool(profile_runtime["persistent"])
        driver._profile_key = profile_runtime["profile_key"]
        driver._profile_ttl_minutes = int(profile_runtime["ttl_minutes"])
        driver._profile_current_proxy_ip = profile_runtime["current_proxy_ip"]
        driver._profile_current_proxy_session_id = profile_runtime["current_proxy_session_id"]
        driver._profile_between_run_ip_changed = bool(profile_runtime["between_run_ip_changed"])
        driver._profile_seed_required = bool(profile_runtime["seed_required"])
        driver._profile_cleanup_policy = str(profile_runtime["cleanup_policy"])
        driver._profile_city_name = city_name
        driver._profile_rsw_id = str(rsw_id) if rsw_id is not None else None
        driver._profile_locale_code = locale_code
        driver._profile_country_code = country_code
        driver._profile_start_url = getattr(driver, "current_url", None)
        driver._runtime_driver_dir = str(runtime_driver_dir) if runtime_driver_dir else None

        if headless_mode:
            logger.debug("Skipping window maximize/position because Chrome is running headless.")
        elif startup_window_size:
            width, height = startup_window_size
            logger.debug(f"Setting startup-aligned window size as {width}x{height} px")
            driver.set_window_size(width, height)
        else:
            logger.debug("Maximizing window...")
            driver.maximize_window()

        if config.webdriver.shift_windows and not headless_mode:
            width, height = (
                config.webdriver.window_size.split(",")
                if config.webdriver.window_size
                else (None, None)
            )
            _shift_window_position(driver, width, height)

        return (driver, country_code) if config.webdriver.country_domain else (driver, None)
    except BaseException:
        if driver:
            try:
                driver.quit()
            except Exception as close_exp:
                logger.debug(f"Failed to close browser after startup exception: {close_exp}")

        if release_runtime_dir(profile_dir) and not bool(profile_runtime["persistent"]):
            shutil.rmtree(profile_dir, ignore_errors=True)
        if runtime_driver_dir and release_runtime_dir(runtime_driver_dir):
            shutil.rmtree(runtime_driver_dir, ignore_errors=True)
        raise


class ChromeOptions(undetected_chromedriver.ChromeOptions):
    """Chrome options wrapper that suppresses UC's hardcoded oversized startup window flags."""

    def add_argument(self, argument):
        if (
            getattr(self, "_suppress_uc_default_window_args", False)
            and argument in UC_DEFAULT_WINDOW_ARGS
        ):
            logger.debug(f"Suppressing undetected_chromedriver default argument: {argument}")
            return

        return super().add_argument(argument)


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
    prefer_headless = bool(getattr(config.webdriver, "prefer_headless", False))
    headless_mode = sys.platform.startswith("linux") and (prefer_headless or not has_display)
    display_dimensions = _get_display_dimensions(os.environ.get("DISPLAY")) if has_display else None
    rotating_window_size = (
        None
        if config.webdriver.window_size
        else _choose_rotating_window_size(display_dimensions)
    )
    startup_window_size: Optional[tuple[int, int]] = None
    if config.webdriver.window_size:
        width, height = config.webdriver.window_size.split(",")
        startup_window_size = (int(width), int(height))
    elif rotating_window_size:
        startup_window_size = (int(rotating_window_size[0]), int(rotating_window_size[1]))
    elif display_dimensions:
        startup_window_size = (int(display_dimensions[0]), int(display_dimensions[1]))

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
        headless2=headless_mode,
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
        _apply_browser_locale_overrides(
            driver,
            locale_code=locale_code,
            accept_language=accept_language,
            user_agent=user_agent,
        )

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
    driver._active_user_agent = user_agent

    # handle window size and position
    if headless_mode:
        if prefer_headless and has_display:
            logger.info(
                "Running SeleniumBase Chrome in configured headless mode on this VPS because "
                "headless is currently outperforming headful mode."
            )
        else:
            logger.warning(
                f"No usable X display found for DISPLAY={os.environ.get('DISPLAY')!r}. "
                "Falling back to headless SeleniumBase Chrome."
            )
        logger.debug("Skipping window maximize/position because SeleniumBase Chrome is headless.")
    elif startup_window_size:
        width, height = startup_window_size
        logger.debug(f"Setting startup-aligned window size as {width}x{height} px")
        driver.set_window_size(int(width), int(height))
    else:
        logger.debug("Maximizing window...")
        driver.maximize_window()

    if config.webdriver.shift_windows and not headless_mode:
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


def _get_driver_exe_path() -> str:
    """Get the path for the chromedriver executable to avoid downloading and patching each time

    :rtype: str
    :returns: Absoulute path of the chromedriver executable
    """

    platform = sys.platform
    prefix = "undetected"
    exe_name = "chromedriver%s"

    if platform.endswith("win32"):
        exe_name %= ".exe"
    if platform.endswith(("linux", "linux2")):
        exe_name %= ""
    if platform.endswith("darwin"):
        exe_name %= ""

    if platform.endswith("win32"):
        dirpath = "~/appdata/roaming/undetected_chromedriver"
    elif "LAMBDA_TASK_ROOT" in os.environ:
        dirpath = "/tmp/undetected_chromedriver"
    elif platform.startswith(("linux", "linux2")):
        dirpath = "~/.local/share/undetected_chromedriver"
    elif platform.endswith("darwin"):
        dirpath = "~/Library/Application Support/undetected_chromedriver"
    else:
        dirpath = "~/.undetected_chromedriver"

    driver_exe_folder = os.path.abspath(os.path.expanduser(dirpath))
    driver_exe_path = os.path.join(driver_exe_folder, "_".join([prefix, exe_name]))

    return driver_exe_path


def _apply_timezone_consistency_script(
    driver: Union[undetected_chromedriver.Chrome, seleniumbase.Driver],
) -> None:
    """Inject only the timezone consistency patches needed before Google loads."""

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
