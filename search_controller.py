import sys
import json
import random
import urllib.parse
import unicodedata
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import re
from time import sleep
from threading import Thread
from typing import Any, Optional, Union

import selenium
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    JavascriptException,
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

import hooks
from adb import adb_controller
from clicklogs_db import ClickLogsDB
from config_reader import config
from logger import logger
from profile_state_db import ProfileStateDB
from stats import SearchStats
from utils import (
    Direction,
    add_cookies,
    add_seed_cookies,
    build_google_seed_cookies,
    domain_matches_url,
    get_ad_allowlist_domains,
    get_ad_denylist_domains,
    get_proxy_exit_ip,
    solve_recaptcha,
    get_random_sleep,
    resolve_redirect,
    boost_requests,
)
from webdriver import execute_presearch_trust_js_code, execute_stealth_js_code


LinkElement = selenium.webdriver.remote.webelement.WebElement
AdList = list[tuple[LinkElement, str, str, int]]
NonAdList = list[LinkElement]
AllLinks = list[Union[AdList, NonAdList]]


class BrowserSessionUnavailableError(RuntimeError):
    """Raised when the local Chrome/WebDriver session disappears mid-run."""


class BrowserClickRecoveryRequired(BrowserSessionUnavailableError):
    """Raised when the search-result click likely happened, but the browser died before landing handling."""

    def __init__(
        self,
        message: str,
        *,
        stage: str,
        click_url: str,
        category: str,
        is_ad_element: bool,
        click_time: str,
        stats_snapshot: SearchStats,
        active_proxy: Optional[str],
        user_agent: Optional[str],
        result_position: Optional[int],
        result_url: Optional[str],
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.click_url = click_url
        self.category = category
        self.is_ad_element = is_ad_element
        self.click_time = click_time
        self.stats_snapshot = deepcopy(stats_snapshot)
        self.active_proxy = active_proxy
        self.user_agent = user_agent
        self.result_position = result_position
        self.result_url = result_url


class SearchController:
    """Search controller for ad clicker

    :type driver: selenium.webdriver
    :param driver: Selenium Chrome webdriver instance
    :type query: str
    :param query: Search query
    :type country_code: str
    :param country_code: Country code for the proxy IP
    """

    URL = "https://www.google.com"

    SEARCH_INPUT = (By.NAME, "q")
    RESULTS_CONTAINER = (By.ID, "appbar")
    COOKIE_DIALOG_BUTTON = (By.TAG_NAME, "button")
    TOP_ADS_CONTAINER = (By.ID, "tads")
    BOTTOM_ADS_CONTAINER = (By.ID, "tadsb")
    AD_RESULTS = (By.CSS_SELECTOR, "div > a")
    AD_TITLE = (By.CSS_SELECTOR, "div[role='heading']")
    ALL_LINKS = (By.CSS_SELECTOR, "div a")
    CAPTCHA_DIALOG = (By.CSS_SELECTOR, "div[aria-label^='Captcha-Dialog']")
    CAPTCHA_IFRAME = (By.CSS_SELECTOR, "iframe[title='Captcha']")
    RECAPTCHA = (By.ID, "recaptcha")
    CAPTCHA_SITEKEY = (By.CSS_SELECTOR, "#recaptcha, [data-sitekey]")
    BLOCK_PAGE_MARKERS = (
        "Our systems have detected unusual traffic",
        "Please try your request again later.",
    )
    CAPTCHA_URL_MARKERS = (
        "/sorry/",
        "/sorry/index",
        "recaptcha",
    )
    RESULTS_READY_SELECTORS = (
        (By.ID, "appbar"),
        (By.ID, "search"),
        (By.ID, "rso"),
        (By.ID, "tads"),
        (By.ID, "center_col"),
    )
    ESTIMATED_LOC_IMG = (
        By.CSS_SELECTOR,
        "img[src^='https://ssl.gstatic.com/oolong/preprompt/Estimated']",
    )
    LOC_CONTINUE_BUTTON = (By.TAG_NAME, "g-raised-button")
    NOT_NOW_BUTTON = (By.CSS_SELECTOR, "g-raised-button[data-ved]")
    BUTTON_CANDIDATE_SELECTORS = (
        (By.TAG_NAME, "button"),
        (By.TAG_NAME, "g-raised-button"),
        (By.CSS_SELECTOR, "[role='button']"),
        (By.CSS_SELECTOR, "input[type='button']"),
        (By.CSS_SELECTOR, "input[type='submit']"),
    )
    COOKIE_CONSENT_ACTION_PHRASES = (
        "accept all",
        "accept",
        "agree",
        "i agree",
        "got it",
        "alle akzeptieren",
        "akzeptieren",
        "ich stimme zu",
        "alle ablehnen",
        "ablehnen",
        "aceitar tudo",
        "aceitar",
        "concordo",
        "rejeitar tudo",
        "rejeitar",
        "aceptar todo",
        "aceptar",
        "rechazar todo",
        "rechazar",
        "reject all",
        "reject",
        "decline all",
        "decline",
    )
    LOCATION_DISMISS_ACTION_PHRASES = (
        "not now",
        "agora nao",
        "agora não",
        "jetzt nicht",
        "ahora no",
    )
    LOCATION_CONTINUE_ACTION_PHRASES = (
        "continue",
        "continuar",
        "weiter",
        "prosseguir",
    )
    UNRELATED_UI_BUTTON_PHRASES = (
        "upload",
        "image",
        "bild",
        "imagem",
        "file",
        "datei",
        "arquivo",
        "language",
        "sprache",
        "idioma",
        "search",
        "google suche",
        "google search",
        "pesquisa",
        "zuruck",
        "zurück",
        "back",
        "voltar",
        "remove",
        "entfernen",
        "microphone",
        "voice",
        "camera",
        "foto",
        "photo",
    )
    WHATSAPP_HREF_HINTS = (
        "wa.me",
        "api.whatsapp.com",
        "web.whatsapp.com",
        "app.whatsapp",
        "whatsapp://",
        "whatsapp.com",
    )
    WHATSAPP_TEXT_HINTS = (
        "whatsapp",
        "whats app",
        "wa.me",
        "wpp",
        "wapp",
    )

    def __init__(
        self,
        driver: selenium.webdriver,
        query: str,
        country_code: Optional[str] = None,
        city_name: Optional[str] = None,
        rsw_id: Optional[str] = None,
        grouped_cycle_id: Optional[str] = None,
    ) -> None:
        self._driver = driver
        self._search_query, self._filter_words = self._process_query(query)
        self._city_name = city_name
        self._rsw_id = str(rsw_id) if rsw_id is not None else None
        self._grouped_cycle_id = grouped_cycle_id
        self._exclude_list = None
        self._ad_allowlist = get_ad_allowlist_domains()
        self._ad_denylist = get_ad_denylist_domains()
        self._random_mouse_enabled = config.behavior.random_mouse
        self._use_custom_cookies = config.behavior.custom_cookies
        self._twocaptcha_apikey = config.behavior.twocaptcha_apikey
        self._max_scroll_limit = config.behavior.max_scroll_limit
        self._hooks_enabled = config.behavior.hooks_enabled

        self._ad_page_min_wait = config.behavior.ad_page_min_wait
        self._ad_page_max_wait = config.behavior.ad_page_max_wait
        self._nonad_page_min_wait = config.behavior.nonad_page_min_wait
        self._nonad_page_max_wait = config.behavior.nonad_page_max_wait

        self._android_device_id = None

        self._stats = SearchStats()
        query_slug = re.sub(r"[^a-z0-9]+", "-", self._search_query.lower()).strip("-") or "query"
        self._run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_{query_slug[:40]}"
        self._click_sequence = 0
        self._screenshot_root = Path.cwd() / ".run_screenshots" / self._run_id
        self._screenshot_root.mkdir(parents=True, exist_ok=True)
        self._screenshot_counter = 0

        if config.behavior.excludes:
            self._exclude_list = [item.strip() for item in config.behavior.excludes.split(",")]
            logger.debug(f"Words to be excluded: {self._exclude_list}")

        if country_code:
            self._set_start_url(country_code)

        self._clicklogs_db_client = ClickLogsDB()
        self._profile_state_db = ProfileStateDB()
        self._profile_key = getattr(self._driver, "_profile_key", None)
        self._profile_cleanup_policy = getattr(self._driver, "_profile_cleanup_policy", "ephemeral")
        self._profile_between_run_ip_changed = bool(
            getattr(self._driver, "_profile_between_run_ip_changed", False)
        )
        self._profile_seed_required = bool(getattr(self._driver, "_profile_seed_required", False))
        self._profile_ttl_minutes = int(getattr(self._driver, "_profile_ttl_minutes", 45) or 45)
        self._profile_preserve_cookie_names = self._build_preserved_cookie_name_set()

        self._load()

    def _record_proxy_ip_checkpoint(self, stage: str, *, abort_on_change: bool = True) -> None:
        active_proxy = getattr(self._driver, "_active_proxy", None)
        if not active_proxy:
            return

        current_proxy_ip = get_proxy_exit_ip(active_proxy, max_retries=1, retry_sleep_seconds=1)
        if not current_proxy_ip:
            logger.warning(f"Proxy IP checkpoint failed at stage={stage}.")
            return

        if not self._stats.initial_proxy_ip:
            self._stats.initial_proxy_ip = current_proxy_ip
            self._stats.latest_proxy_ip = current_proxy_ip
            logger.info(
                f"Proxy IP checkpoint [{stage}]: initial exit IP set to {current_proxy_ip}"
            )
            return

        previous_proxy_ip = self._stats.latest_proxy_ip or self._stats.initial_proxy_ip
        self._stats.latest_proxy_ip = current_proxy_ip
        logger.info(
            f"Proxy IP checkpoint [{stage}]: current={current_proxy_ip}, previous={previous_proxy_ip}"
        )

        if current_proxy_ip == self._stats.initial_proxy_ip:
            return

        self._stats.ip_changed_mid_session = True
        logger.error(
            "Proxy exit IP changed mid-session: "
            f"initial={self._stats.initial_proxy_ip}, current={current_proxy_ip}, stage={stage}"
        )
        self._save_step_screenshot(f"{stage}_ip_changed")

        if abort_on_change:
            logger.info("Stopping run because proxy exit IP changed mid-session.")
            self._driver.quit()
            raise SystemExit()

    def search_for_ads(
        self, non_ad_domains: Optional[list[str]] = None
    ) -> tuple[AdList, NonAdList]:
        """Start search for the given query and return ads if any

        Also, get non-ad links including domains given.

        :type non_ad_domains: list
        :param non_ad_domains: List of domains to select for non-ad links
        :rtype: tuple
        :returns: Tuple of [(ad, ad_link, ad_title), non_ad_links]
        """

        if self._use_custom_cookies:
            self._driver.delete_all_cookies()
            add_cookies(self._driver)

            for cookie in self._driver.get_cookies():
                logger.debug(cookie)

        self._wait_for_page_settle()
        self._ensure_browser_session_alive("after_initial_settle")
        self._save_step_screenshot("after_query_sent")
        self._ensure_browser_session_alive("after_initial_screenshot")
        self._close_cookie_dialog()
        self._ensure_browser_session_alive("after_cookie_dialog")
        self._wait_for_page_settle()
        self._ensure_browser_session_alive("after_second_settle")
        self._record_proxy_ip_checkpoint("session_start")
        self._abort_if_google_blocked("search_start")

        logger.info(f"Starting search for '{self._search_query}'")
        sleep(get_random_sleep(1, 2) * config.behavior.wait_factor)

        if not self._submit_search_query():
            self._abort_if_google_blocked("search_input_missing")
            logger.warning("Search input was not ready. Falling back to direct search URL.")
            self._open_search_results_directly()

        self._wait_for_page_settle(timeout=6)
        self._check_captcha()
        self._abort_if_google_blocked("after_query_submit")

        # wait 2 to 3 seconds before checking if results were loaded
        sleep(get_random_sleep(2, 3) * config.behavior.wait_factor)

        if not self._results_page_ready():
            self._close_cookie_dialog()
            if not self._results_page_ready():
                if not self._submit_search_query():
                    logger.warning(
                        "Results are still not ready after retrying the homepage search box. "
                        "Falling back to direct search URL."
                    )
                    self._open_search_results_directly()
                self._check_captcha()
                self._abort_if_google_blocked("after_retry_submit")
                sleep(get_random_sleep(2, 3) * config.behavior.wait_factor)

        if self._hooks_enabled:
            hooks.after_query_sent_hook(self._driver, self._search_query)

        ad_links = []
        non_ad_links = []
        shopping_ad_links = []

        try:
            wait = WebDriverWait(self._driver, timeout=5)
            results_loaded = wait.until(lambda driver: self._results_page_ready())

            if results_loaded:
                if self._hooks_enabled:
                    hooks.results_ready_hook(self._driver)

                self._save_step_screenshot("results_loaded")
                self._close_choose_location_popup()
                logger.debug("Skipping random scroll and mouse interactions for browser stability.")

                self._close_choose_location_popup()

                if config.behavior.check_shopping_ads:
                    shopping_ad_links = self._get_shopping_ad_links()

                ad_links = self._get_ad_links()
                non_ad_links = self._get_non_ad_links(ad_links, non_ad_domains)

        except TimeoutException:
            logger.error("Timed out waiting for results!")
            self.end_search()

        return (ad_links, non_ad_links, shopping_ad_links)

    def click_shopping_ads(self, shopping_ads: AdList) -> None:
        """Click shopping ads if there are any

        :type shopping_ads: AdList
        :param shopping_ads: List of (ad, ad_link, ad_title) tuples
        """

        # store the ID of the original window
        original_window_handle = self._driver.current_window_handle

        for ad in shopping_ads:
            try:
                ad_link_element = ad[0]
                ad_link = ad[1]
                ad_title = ad[2].replace("\n", " ")
                result_position = ad[3]
                logger.info(f"Clicking to [{ad_title}]({ad_link})...")
                self._save_step_screenshot("shopping_before_click")

                if self._hooks_enabled:
                    hooks.before_ad_click_hook(self._driver)

                if config.behavior.send_to_android and self._android_device_id:
                    self._handle_android_click(
                        ad_link_element,
                        ad_link,
                        True,
                        category="Shopping",
                        result_position=result_position,
                        result_url=ad_link,
                    )
                else:
                    self._handle_browser_click(
                        ad_link_element,
                        ad_link,
                        True,
                        original_window_handle,
                        category="Shopping",
                        result_position=result_position,
                        result_url=ad_link,
                    )
                self._save_step_screenshot("shopping_after_click")

            except BrowserSessionUnavailableError:
                raise
            except Exception as exp:
                if self._is_browser_session_unavailable_exception(exp):
                    self._abort_due_to_browser_unavailable("shopping_ad_click", exp)
                logger.debug(f"Failed to click ad element [{ad_title}]!")

    def click_links(self, links: AllLinks) -> None:
        """Click links

        :type links: AllLinks
        :param links: List of [(ad, ad_link, ad_title), non_ad_links]
        """

        execute_stealth_js_code(self._driver)

        # store the ID of the original window
        original_window_handle = self._driver.current_window_handle

        for link in links:
            is_ad_element = isinstance(link, tuple)

            try:
                link_element, link_url, ad_title, result_position = self._extract_link_info(
                    link, is_ad_element
                )

                if self._hooks_enabled and is_ad_element:
                    hooks.before_ad_click_hook(self._driver)

                logger.info(
                    f"Clicking to {'[' + ad_title + '](' + link_url + ')' if is_ad_element else '[' + link_url + ']'}..."
                )
                category = "ad" if is_ad_element else "non_ad"
                self._save_step_screenshot(f"{category}_before_click")

                category = "Ad" if is_ad_element else "Non-ad"

                if config.behavior.send_to_android and self._android_device_id:
                    self._handle_android_click(
                        link_element,
                        link_url,
                        is_ad_element,
                        category,
                        result_position=result_position,
                        result_url=link_url,
                    )
                else:
                    self._handle_browser_click(
                        link_element,
                        link_url,
                        is_ad_element,
                        original_window_handle,
                        category,
                        result_position=result_position,
                        result_url=link_url,
                    )
                self._save_step_screenshot(
                    f"{'ad' if is_ad_element else 'non_ad'}_after_click"
                )

                # scroll the page to avoid elements remain outside of the view
                self._driver.execute_script("arguments[0].scrollIntoView(true);", link_element)

            except StaleElementReferenceException:
                logger.debug(
                    f"Ad element [{ad_title if is_ad_element else link_url}] has changed. "
                    "Skipping scroll into view..."
                )

            except BrowserSessionUnavailableError:
                raise
            except Exception as exp:
                if self._is_browser_session_unavailable_exception(exp):
                    self._abort_due_to_browser_unavailable("search_result_click", exp)
                logger.error(f"Failed to click on [{ad_title if is_ad_element else link_url}]!")

    def _save_step_screenshot(self, step_name: str) -> None:
        """Save flow screenshots for debugging before/after click steps."""

        if not self._driver:
            return

        try:
            self._screenshot_counter += 1
            safe_step_name = re.sub(r"[^a-zA-Z0-9_\\-]+", "_", step_name).strip("_") or "step"
            browser_label = (
                f"browser_{self._stats.browser_id}" if self._stats.browser_id is not None else "browser_single"
            )
            target_dir = self._screenshot_root / browser_label
            target_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{self._screenshot_counter:04d}_{safe_step_name}.png"
            screenshot_path = target_dir / filename
            self._driver.save_screenshot(str(screenshot_path))
            logger.debug(f"Saved run screenshot: {screenshot_path}")
        except Exception as exp:
            if (
                not step_name.endswith("_browser_unavailable")
                and self._is_browser_session_unavailable_exception(exp)
            ):
                self._abort_due_to_browser_unavailable(f"{step_name}_screenshot", exp)
            logger.debug(f"Failed to save step screenshot ({step_name}): {exp}")

    def _on_captcha_poll(self, response_text: str, retry_count: int) -> None:
        """Capture captcha page state while polling 2captcha results."""

        normalized = response_text.strip().lower()
        if normalized.startswith("ok|"):
            status = "ok"
        elif "not_ready" in normalized:
            status = "not_ready"
        else:
            status = normalized.replace("|", "_").replace(" ", "_")[:40] or "unknown"

        self._save_step_screenshot(f"captcha_poll_{retry_count:02d}_{status}")

    def _extract_link_info(self, link: Any, is_ad_element: bool) -> tuple:
        """Extract link information

        :type link: tuple(ad, ad_link, ad_title) or LinkElement
        :param link: (ad, ad_link, ad_title) for ads LinkElement for non-ads
        :type is_ad_element: bool
        :param is_ad_element: Whether it is an ad or non-ad link
        :rtype: tuple
        :returns: (link_element, link_url, ad_title) tuple
        """

        if is_ad_element:
            link_element = link[0]
            link_url = link[1]
            ad_title = link[2]
            result_position = link[3]
        else:
            link_element = link
            link_url = link_element.get_attribute("href")
            ad_title = None
            result_position = None

        return (link_element, link_url, ad_title, result_position)

    def _extract_ad_title(self, ad: LinkElement) -> str:
        """Extract a resilient ad title from the SERP card."""

        try:
            title = ad.find_element(*self.AD_TITLE).text.strip()
            if title:
                return title
        except NoSuchElementException:
            pass

        for selector in ("h3", "a h3", "[aria-label]"):
            try:
                element = ad.find_element(By.CSS_SELECTOR, selector)
                text = (element.text or element.get_attribute("aria-label") or "").strip()
                if text:
                    return text
            except NoSuchElementException:
                continue

        fallback = (
            ad.get_attribute("data-pcu")
            or ad.get_attribute("href")
            or "Untitled ad"
        )
        logger.debug(f"Falling back to ad title from URL/attributes: {fallback}")
        return fallback

    def _handle_android_click(
        self,
        link_element: selenium.webdriver.remote.webelement.WebElement,
        link_url: str,
        is_ad_element: bool,
        category: str = "Ad",
        result_position: Optional[int] = None,
        result_url: Optional[str] = None,
    ) -> None:
        """Handle opening link on Android device

        :type link_element: selenium.webdriver.remote.webelement.WebElement
        :param link_element: Link element
        :type link_url: str
        :param link_url: Canonical url for the clicked link
        :type is_ad_element: bool
        :param is_ad_element: Whether it is an ad or non-ad link
        :type category: str
        :param category: Specifies link category as Ad, Non-ad, or Shopping
        """

        url = link_url if category == "Shopping" else link_element.get_attribute("href")
        logger.info(f"{category} click target URL: {url}")

        url = resolve_redirect(url)
        logger.info(f"{category} final resolved URL: {url}")

        adb_controller.open_url(url, self._android_device_id)

        click_time = datetime.now().strftime("%H:%M:%S")

        # wait a little before starting random actions
        sleep(get_random_sleep(2, 3) * config.behavior.wait_factor)

        logger.debug(f"Current url on device: {url}")

        if self._hooks_enabled and category in ("Ad", "Shopping"):
            hooks.after_ad_click_hook(self._driver)

        self._start_random_scroll_thread()

        site_url = (
            "/".join(url.split("/", maxsplit=3)[:3])
            if category in ("Shopping", "Non-ad")
            else link_url
        )

        self._update_click_stats(
            site_url,
            click_time,
            category,
            result_position=result_position,
            result_url=result_url or url,
        )

        if config.behavior.request_boost:
            boost_requests(url)

        wait_time = self._get_wait_time(is_ad_element) * config.behavior.wait_factor
        logger.debug(f"Waiting {wait_time} seconds on {category.lower()} page...")
        sleep(wait_time)

        adb_controller.close_browser()
        sleep(get_random_sleep(0.5, 1) * config.behavior.wait_factor)

    def _handle_browser_click(
        self,
        link_element: selenium.webdriver.remote.webelement.WebElement,
        link_url: str,
        is_ad_element: bool,
        original_window_handle: str,
        category: str = "Ad",
        result_position: Optional[int] = None,
        result_url: Optional[str] = None,
    ) -> None:
        """Handle clicking in the browser

        :type link_element: selenium.webdriver.remote.webelement.WebElement
        :param link_element: Link element
        :type link_url: str
        :param link_url: Canonical url for the clicked link
        :type is_ad_element: bool
        :param is_ad_element: Whether it is an ad or non-ad link
        :type original_window_handle: str
        :param original_window_handle: Window handle for the search results tab
        :type category: str
        :param category: Specifies link category as Ad, Non-ad, or Shopping
        """

        click_time = datetime.now().strftime("%H:%M:%S")
        clicked_target_url = link_url if is_ad_element else link_element.get_attribute("href")
        tab_opened = False
        click_stage = "before_open_tab"

        try:
            self._open_link_in_new_tab(link_element)
            click_stage = "after_open_tab"
            self._ensure_browser_session_alive("browser_click_after_open_tab")

            if len(self._driver.window_handles) != 2:
                logger.debug("Couldn't click! Scrolling element into view...")
                self._driver.execute_script("arguments[0].scrollIntoView(true);", link_element)
                self._open_link_in_new_tab(link_element)
                click_stage = "after_retry_open_tab"
                self._ensure_browser_session_alive("browser_click_after_retry_open_tab")

            if len(self._driver.window_handles) != 2:
                logger.debug(f"Failed to open '{link_url}' in a new tab!")
                return
            else:
                logger.debug("Opened link in a new tab. Switching to tab...")
                tab_opened = True

            for window_handle in self._driver.window_handles:
                if window_handle != original_window_handle:
                    self._driver.switch_to.window(window_handle)
                    click_stage = "after_tab_switch"
                    self._ensure_browser_session_alive("browser_click_after_tab_switch")
                    self._save_step_screenshot(f"{category.lower().replace('-', '_')}_landing_opened")
                    click_stage = "landing_opened"
                    self._ensure_browser_session_alive("browser_click_after_landing_opened")

                    sleep(get_random_sleep(3, 5) * config.behavior.wait_factor)
                    self._ensure_browser_session_alive("browser_click_after_landing_wait")
                    final_landed_url = self._driver.current_url
                    logger.info(f"{category} click target URL: {clicked_target_url}")
                    logger.info(f"{category} final landed URL: {final_landed_url}")
                    logger.debug(f"Current url on new tab: {final_landed_url}")

                    if self._hooks_enabled and category in ("Ad", "Shopping"):
                        hooks.after_ad_click_hook(self._driver)

                    self._maybe_click_whatsapp_interaction(category)
                    self._ensure_browser_session_alive("browser_click_after_whatsapp")
                    self._start_random_action_threads()
                    self._ensure_browser_session_alive("browser_click_after_random_actions")

                    url = (
                        "/".join(final_landed_url.split("/", maxsplit=3)[:3])
                        if category == "Shopping"
                        else (link_url if is_ad_element else final_landed_url)
                    )

                    self._update_click_stats(
                        url,
                        click_time,
                        category,
                        final_url=final_landed_url,
                        result_position=result_position,
                        result_url=result_url or clicked_target_url or link_url,
                    )

                    if config.behavior.request_boost:
                        boost_requests(final_landed_url)

                    wait_time = self._get_wait_time(is_ad_element) * config.behavior.wait_factor
                    logger.debug(f"Waiting {wait_time} seconds on {category.lower()} page...")
                    sleep(wait_time)
                    self._ensure_browser_session_alive("browser_click_before_landing_close")
                    self._save_step_screenshot(
                        f"{category.lower().replace('-', '_')}_landing_before_close"
                    )

                    self._driver.close()
                    break

            # go back to the original window
            self._driver.switch_to.window(original_window_handle)
            sleep(get_random_sleep(1, 1.5) * config.behavior.wait_factor)
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                if tab_opened and category in ("Ad", "Shopping"):
                    logger.warning(
                        "Browser session disappeared after the result click opened a new tab. "
                        "Scheduling a fresh-browser landing recovery."
                    )
                    raise BrowserClickRecoveryRequired(
                        str(exp),
                        stage=click_stage,
                        click_url=clicked_target_url or link_url,
                        category=category,
                        is_ad_element=is_ad_element,
                        click_time=click_time,
                        stats_snapshot=self._stats,
                        active_proxy=getattr(self._driver, "_active_proxy", None),
                        user_agent=getattr(self._driver, "_active_user_agent", None),
                        result_position=result_position,
                        result_url=result_url or clicked_target_url or link_url,
                    ) from exp
                self._abort_due_to_browser_unavailable("browser_click", exp)
            raise

    def recover_interrupted_click(
        self,
        click_url: str,
        *,
        category: str,
        is_ad_element: bool,
        click_time: str,
        result_position: Optional[int] = None,
        result_url: Optional[str] = None,
    ) -> None:
        """Recover a click whose landing handling was interrupted by a local browser crash."""

        logger.warning(
            "Recovering interrupted %s click in a fresh browser session: %s",
            category.lower(),
            click_url,
        )

        execute_stealth_js_code(self._driver)

        if config.webdriver.use_seleniumbase:
            self._driver.uc_open_with_reconnect(click_url, reconnect_time=3)
        else:
            self._driver.get(click_url)

        self._ensure_browser_session_alive("click_recovery_after_direct_open")
        self._wait_for_page_settle(timeout=6)
        self._ensure_browser_session_alive("click_recovery_after_settle")
        self._save_step_screenshot(f"{category.lower().replace('-', '_')}_landing_opened_recovery")

        sleep(get_random_sleep(3, 5) * config.behavior.wait_factor)
        self._ensure_browser_session_alive("click_recovery_after_landing_wait")

        final_landed_url = self._driver.current_url
        logger.info(f"{category} recovery target URL: {click_url}")
        logger.info(f"{category} recovery landed URL: {final_landed_url}")

        if self._hooks_enabled and category in ("Ad", "Shopping"):
            hooks.after_ad_click_hook(self._driver)

        self._maybe_click_whatsapp_interaction(category)
        self._ensure_browser_session_alive("click_recovery_after_whatsapp")
        self._start_random_action_threads()
        self._ensure_browser_session_alive("click_recovery_after_random_actions")

        url = (
            "/".join(final_landed_url.split("/", maxsplit=3)[:3])
            if category == "Shopping"
            else (click_url if is_ad_element else final_landed_url)
        )
        self._update_click_stats(
            url,
            click_time,
            category,
            final_url=final_landed_url,
            result_position=result_position,
            result_url=result_url or click_url,
        )

        if config.behavior.request_boost:
            boost_requests(final_landed_url)

        wait_time = self._get_wait_time(is_ad_element) * config.behavior.wait_factor
        logger.debug(f"Waiting {wait_time} seconds on recovered {category.lower()} page...")
        sleep(wait_time)
        self._ensure_browser_session_alive("click_recovery_before_landing_close")
        self._save_step_screenshot(
            f"{category.lower().replace('-', '_')}_landing_before_close_recovery"
        )

    def _maybe_click_whatsapp_interaction(self, category: str) -> None:
        """Optionally click a visible WhatsApp-style CTA on the landing page."""

        candidates = self._find_whatsapp_candidates()
        if not candidates:
            logger.debug("No WhatsApp interaction candidates found on landing page.")
            return

        top_score = candidates[0]["score"]
        top_candidates = [candidate for candidate in candidates if candidate["score"] == top_score]
        candidate = random.choice(top_candidates)

        current_handle = self._driver.current_window_handle
        before_handles = list(self._driver.window_handles)
        before_url = self._driver.current_url
        element = candidate["element"]

        logger.info(
            "Trying WhatsApp interaction on landing page: "
            f"tag={candidate['tag']}, text={candidate['text']!r}, href={candidate['href']!r}"
        )
        self._save_step_screenshot(f"{category.lower().replace('-', '_')}_whatsapp_before_click")

        try:
            self._driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                element,
            )
            sleep(get_random_sleep(0.5, 1) * config.behavior.wait_factor)
            try:
                element.click()
            except (
                ElementNotInteractableException,
                ElementClickInterceptedException,
                StaleElementReferenceException,
                WebDriverException,
            ):
                self._driver.execute_script("arguments[0].click();", element)
        except Exception as exp:
            logger.debug(f"WhatsApp interaction click attempt failed: {exp}")
            return

        sleep(get_random_sleep(1.5, 2.5) * config.behavior.wait_factor)

        new_handles = [handle for handle in self._driver.window_handles if handle not in before_handles]
        if new_handles:
            logger.info(f"WhatsApp interaction opened {len(new_handles)} extra tab(s).")
            for index, handle in enumerate(new_handles, start=1):
                try:
                    self._driver.switch_to.window(handle)
                    logger.info(
                        f"WhatsApp interaction tab {index} URL: {self._driver.current_url}"
                    )
                    self._save_step_screenshot(
                        f"{category.lower().replace('-', '_')}_whatsapp_tab_{index:02d}"
                    )
                    sleep(get_random_sleep(1.5, 2.5) * config.behavior.wait_factor)
                    self._driver.close()
                except Exception as exp:
                    logger.debug(f"Failed to inspect/close WhatsApp interaction tab: {exp}")
            self._driver.switch_to.window(current_handle)
            self._wait_for_page_settle(timeout=4)
            return

        after_url = self._driver.current_url
        if after_url != before_url:
            logger.info(f"WhatsApp interaction changed current tab URL to: {after_url}")
            self._save_step_screenshot(f"{category.lower().replace('-', '_')}_whatsapp_same_tab")
            sleep(get_random_sleep(1.5, 2.5) * config.behavior.wait_factor)
            try:
                self._driver.back()
                self._wait_for_page_settle(timeout=4)
            except Exception as exp:
                logger.debug(f"Failed to navigate back after WhatsApp interaction: {exp}")
            return

        logger.debug("WhatsApp interaction stayed on the same page without URL change.")

    def _find_whatsapp_candidates(self) -> list[dict[str, object]]:
        """Find visible, clickable WhatsApp-style CTA elements on the current page."""

        try:
            elements = self._driver.find_elements(By.CSS_SELECTOR, "a, button, [role='button']")
        except Exception as exp:
            logger.debug(f"Failed to enumerate WhatsApp interaction candidates: {exp}")
            return []

        candidates: list[dict[str, object]] = []
        seen_signatures: set[tuple[str, str, str]] = set()

        for element in elements:
            try:
                if not element.is_displayed() or not element.is_enabled():
                    continue

                href = (element.get_attribute("href") or "").strip()
                text = (element.text or "").strip()
                aria_label = (element.get_attribute("aria-label") or "").strip()
                title = (element.get_attribute("title") or "").strip()
                name = (element.get_attribute("name") or "").strip()
                element_id = (element.get_attribute("id") or "").strip()
                class_name = (element.get_attribute("class") or "").strip()
                tag_name = (element.tag_name or "").strip().lower()

                href_lower = href.lower()
                text_lower = " ".join(
                    part
                    for part in (text, aria_label, title, name)
                    if part
                ).lower()
                attr_lower = " ".join(part for part in (element_id, class_name) if part).lower()

                score = 0
                if any(token in href_lower for token in self.WHATSAPP_HREF_HINTS):
                    score += 100
                if any(token in text_lower for token in self.WHATSAPP_TEXT_HINTS):
                    score += 50
                if any(token in attr_lower for token in self.WHATSAPP_TEXT_HINTS):
                    score += 20
                if tag_name == "a":
                    score += 10
                if href_lower.startswith(("https://", "http://", "whatsapp://")):
                    score += 5

                if score <= 0:
                    continue

                signature = (tag_name, href_lower, text_lower)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)

                candidates.append(
                    {
                        "score": score,
                        "element": element,
                        "tag": tag_name,
                        "href": href,
                        "text": text or aria_label or title or name or element_id or class_name,
                    }
                )
            except (
                StaleElementReferenceException,
                ElementNotInteractableException,
                WebDriverException,
            ):
                continue

        candidates.sort(key=lambda candidate: int(candidate["score"]), reverse=True)
        return candidates

    def _open_link_in_new_tab(
        self, link_element: selenium.webdriver.remote.webelement.WebElement
    ) -> None:
        """Open the link in a new browser tab

        :type link_element: selenium.webdriver.remote.webelement.WebElement
        :param link_element: Link element
        """

        platform = sys.platform
        control_command_key = Keys.COMMAND if platform.endswith("darwin") else Keys.CONTROL

        try:
            actions = ActionChains(self._driver)
            actions.move_to_element(link_element)
            actions.key_down(control_command_key)
            actions.click()
            actions.key_up(control_command_key)
            actions.perform()

            sleep(get_random_sleep(0.5, 1) * config.behavior.wait_factor)

        except JavascriptException as exp:
            error_message = str(exp).split("\n")[0]

            if "has no size and location" in error_message:
                logger.error(
                    f"Failed to click element[{link_element.get_attribute('outerHTML')}]! "
                    "Skipping..."
                )
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("open_link_in_new_tab", exp)
            raise

    def _get_wait_time(self, is_ad_element: bool) -> int:
        """Get wait time based on whether the link is an ad or non-ad

        :type is_ad_element: bool
        :param is_ad_element: Whether it is an ad or non-ad link
        :rtype: int
        :returns: Randomly selected number from the given range
        """

        if is_ad_element:
            return random.choice(range(self._ad_page_min_wait, self._ad_page_max_wait))
        else:
            return random.choice(range(self._nonad_page_min_wait, self._nonad_page_max_wait))

    def _next_click_id(self) -> str:
        self._click_sequence += 1
        return f"{self._run_id}_click_{self._click_sequence:03d}"

    def _update_click_stats(
        self,
        url: str,
        click_time: str,
        category: str,
        final_url: str | None = None,
        result_position: Optional[int] = None,
        result_url: Optional[str] = None,
    ) -> None:
        """Update click statistics

        :type url: str
        :param url: Clicked link url to save db
        :type click_time: str
        :param click_time: Click time in hh:mm:ss format
        :type category: str
        :param category: Specifies link category as Ad, Non-ad, or Shopping
        """

        if category == "Ad":
            self._stats.ads_clicked += 1
        elif category == "Non-ad":
            self._stats.non_ads_clicked += 1
        elif category == "Shopping":
            self._stats.shopping_ads_clicked += 1

        click_id = self._next_click_id()
        self._clicklogs_db_client.save_click(
            site_url=url,
            category=category,
            query=self._search_query,
            click_time=click_time,
            city_name=self._city_name,
            rsw_id=self._rsw_id,
            final_url=final_url,
            grouped_cycle_id=self._grouped_cycle_id,
            click_id=click_id,
            search_run_id=self._run_id,
            result_position=result_position,
            result_url=result_url or url,
        )

    def _start_random_scroll_thread(self) -> None:
        """Start a thread for random swipes on Android device"""

        random_scroll_thread = Thread(target=self._make_random_swipes)
        random_scroll_thread.start()
        random_scroll_thread.join(
            timeout=float(max(self._ad_page_max_wait, self._nonad_page_max_wait))
        )

    def _start_random_action_threads(self) -> None:
        """Start threads for random actions on browser"""

        random_scroll_thread = Thread(target=self._make_random_scrolls)
        random_scroll_thread.start()
        random_mouse_thread = Thread(target=self._make_random_mouse_movements)
        random_mouse_thread.start()
        random_scroll_thread.join(
            timeout=float(max(self._ad_page_max_wait, self._nonad_page_max_wait))
        )
        random_mouse_thread.join(
            timeout=float(max(self._ad_page_max_wait, self._nonad_page_max_wait))
        )

    def end_search(self) -> None:
        """Close the browser.

        Delete cookies and cache before closing.
        """

        if self._driver:
            try:
                self._update_profile_state_from_run()
                self._delete_cache_and_cookies()
                self._driver.quit()

            except Exception as exp:
                logger.debug(exp)

            self._driver = None

    def _load(self) -> None:
        """Load Google main page"""

        execute_presearch_trust_js_code(self._driver)
        if config.webdriver.use_seleniumbase:
            self._driver.uc_open_with_reconnect(self.URL, reconnect_time=3)
        else:
            self._driver.get(self.URL)
        self._apply_profile_startup_bootstrap()

    def _build_preserved_cookie_name_set(self) -> set[str]:
        names: set[str] = set()
        if bool(getattr(config.webdriver, "profile_preserve_consent_cookies", True)):
            names.update({"CONSENT", "SOCS"})
        if bool(getattr(config.webdriver, "profile_preserve_locale_cookies", True)):
            names.add("PREF")
        return names

    def _is_google_url(self, url: str) -> bool:
        try:
            host = urllib.parse.urlparse(url).netloc.lower()
        except Exception:
            return False
        return "google." in host

    def _open_google_surface_for_profile_ops(self) -> None:
        try:
            current_url = self._driver.current_url or ""
        except Exception:
            current_url = ""

        if self._is_google_url(current_url):
            return

        if config.webdriver.use_seleniumbase:
            self._driver.uc_open_with_reconnect(self.URL, reconnect_time=3)
        else:
            self._driver.get(self.URL)
        self._wait_for_page_settle(timeout=4)

    def _apply_profile_startup_bootstrap(self) -> None:
        if not self._profile_key:
            return

        changed_state = False
        self._open_google_surface_for_profile_ops()

        if (
            self._profile_between_run_ip_changed
            and bool(getattr(config.webdriver, "profile_soft_cleanup_on_ip_change", True))
        ):
            changed_state = self._apply_between_run_ip_change_hygiene() or changed_state

        if (
            self._profile_seed_required
            and bool(getattr(config.webdriver, "profile_seed_google_consent", False))
        ):
            changed_state = self._apply_seed_cookies_for_cold_profile() or changed_state

        if changed_state:
            self._driver.refresh()
            self._wait_for_page_settle(timeout=4)

    def _apply_between_run_ip_change_hygiene(self) -> bool:
        self._open_google_surface_for_profile_ops()
        deleted_count = 0

        try:
            cookies = self._driver.get_cookies()
        except Exception as exp:
            logger.debug(f"Failed to inspect Google cookies for IP-change hygiene: {exp}")
            return False

        for cookie in cookies:
            cookie_name = str(cookie.get("name") or "").strip()
            if cookie_name in self._profile_preserve_cookie_names:
                continue
            try:
                self._driver.delete_cookie(cookie_name)
                deleted_count += 1
            except Exception as exp:
                logger.debug(f"Failed to delete cookie '{cookie_name}' during hygiene: {exp}")

        try:
            self._driver.execute_cdp_cmd("Network.clearBrowserCache", {})
        except Exception as exp:
            logger.debug(f"Failed to clear browser cache during IP-change hygiene: {exp}")

        for script in (
            "window.sessionStorage.clear();",
            "window.localStorage.clear();",
        ):
            try:
                self._driver.execute_script(script)
            except Exception as exp:
                logger.debug(f"Failed to execute startup storage hygiene script: {exp}")

        logger.info(
            "Applied between-run IP-change hygiene for profile '%s': deleted %d Google cookie(s), "
            "preserved %d cookie name(s).",
            self._profile_key,
            deleted_count,
            len(self._profile_preserve_cookie_names),
        )
        return True

    def _apply_seed_cookies_for_cold_profile(self) -> bool:
        locale_code = getattr(self._driver, "_profile_locale_code", None)
        country_code = getattr(self._driver, "_profile_country_code", None)
        domain_hint = urllib.parse.urlparse(self.URL).netloc or ".google.com"
        cookies = build_google_seed_cookies(
            locale_code=locale_code,
            country_code=country_code,
            domain_hint=domain_hint,
            include_consent=bool(getattr(config.webdriver, "profile_seed_google_consent", False)),
        )
        added_count = add_seed_cookies(self._driver, cookies)
        if added_count and self._profile_key:
            self._profile_state_db.mark_seeded(self._profile_key)
            logger.info(
                "Applied %d Google seed cookie(s) to cold profile '%s'.",
                added_count,
                self._profile_key,
            )
            return True
        return False

    def _update_profile_state_from_run(self) -> None:
        if not self._profile_key:
            return

        current_proxy_ip = (
            self._stats.latest_proxy_ip
            or self._stats.initial_proxy_ip
            or getattr(self._driver, "_profile_current_proxy_ip", None)
        )
        current_proxy_session_id = getattr(self._driver, "_profile_current_proxy_session_id", None)
        self._profile_state_db.record_proxy_observation(
            self._profile_key,
            proxy_ip=current_proxy_ip,
            proxy_session_id=current_proxy_session_id,
            ttl_minutes=self._profile_ttl_minutes,
        )

        risk_delta = 0
        recycle_reason = None
        if self._stats.ip_changed_mid_session:
            risk_delta += 4
            recycle_reason = "mid_session_ip_change"
        elif self._stats.google_blocked_after_captcha:
            risk_delta += 3
            recycle_reason = "google_block_after_captcha"
        elif self._stats.captcha_seen and not self._stats.captcha_accepted:
            risk_delta += 2
            recycle_reason = "captcha_not_accepted"
        elif self._stats.captcha_seen:
            risk_delta += 1
        elif self._stats.ads_clicked or self._stats.shopping_ads_clicked:
            risk_delta -= 1
        else:
            risk_delta = 0

        next_risk_score = self._profile_state_db.adjust_risk(
            self._profile_key,
            risk_delta,
            reason=recycle_reason,
        )

        should_recycle = False
        if (
            self._stats.ip_changed_mid_session
            and bool(getattr(config.webdriver, "profile_recycle_on_mid_session_ip_change", True))
        ):
            should_recycle = True
            recycle_reason = recycle_reason or "mid_session_ip_change"
        elif next_risk_score >= int(getattr(config.webdriver, "profile_risk_score_threshold", 6) or 6):
            should_recycle = True
            recycle_reason = recycle_reason or "risk_threshold"

        if should_recycle:
            self._profile_state_db.mark_recycle(self._profile_key, recycle_reason or "recycle")
            self._driver._runtime_profile_recycle = True
            self._driver._profile_cleanup_policy = "city_profile_recycle"
            self._profile_cleanup_policy = "city_profile_recycle"
            logger.warning(
                "Marked reusable profile '%s' for recycle: reason=%s, risk_score=%s",
                self._profile_key,
                recycle_reason,
                next_risk_score,
            )
        else:
            self._driver._runtime_profile_recycle = False

    def _get_shopping_ad_links(self) -> AdList:
        """Extract shopping ad links to click if exists

        :rtype: AdList
        :returns: List of (ad, ad_link, ad_title) tuples
        """

        ads = []

        try:
            logger.info("Checking shopping ads...")

            # for mobile user-agents
            mobile_shopping_ads = self._driver.find_elements(By.CLASS_NAME, "pla-unit-container")
            if mobile_shopping_ads:
                for shopping_index, shopping_ad in enumerate(mobile_shopping_ads[:5], start=1):
                    ad = shopping_ad.find_element(By.TAG_NAME, "a")
                    shopping_ad_link = ad.get_attribute("href")
                    shopping_ad_title = shopping_ad.text.strip()
                    shopping_ad_target_link = shopping_ad_link

                    ad_fields = (
                        shopping_ad,
                        shopping_ad_link,
                        shopping_ad_title,
                        shopping_ad_target_link,
                        shopping_index,
                    )
                    logger.debug(ad_fields)

                    ads.append(ad_fields)

            else:
                commercial_unit_containers = self._driver.find_elements(
                    By.CLASS_NAME,
                    "cu-container",
                )
                if not commercial_unit_containers:
                    logger.info("No shopping ads are shown!")
                    return []

                commercial_unit_container = commercial_unit_containers[0]
                shopping_ads = commercial_unit_container.find_elements(By.CLASS_NAME, "pla-unit")

                for shopping_index, shopping_ad in enumerate(shopping_ads[:5], start=1):
                    ad = shopping_ad.find_element(By.TAG_NAME, "a")
                    shopping_ad_link = ad.get_attribute("href")

                    ad_data_element = shopping_ad.find_element(By.CSS_SELECTOR, "a:nth-child(2)")
                    shopping_ad_title = ad_data_element.get_attribute("aria-label")
                    shopping_ad_target_link = ad_data_element.get_attribute("href")

                    ad_fields = (
                        shopping_ad,
                        shopping_ad_link,
                        shopping_ad_title,
                        shopping_ad_target_link,
                        shopping_index,
                    )
                    logger.debug(ad_fields)

                    ads.append(ad_fields)

            self._stats.shopping_ads_found = len(ads)

            if not ads:
                return []

            # if there are filter words given, filter results accordingly
            filtered_ads = []

            if self._filter_words:
                for ad in ads:
                    ad_title = ad[2].replace("\n", " ")
                    ad_link = ad[3]

                    for word in self._filter_words:
                        if word in ad_link or word in ad_title.lower():
                            if ad not in filtered_ads:
                                logger.debug(f"Filtering [{ad_title}]: {ad_link}")
                                self._stats.num_filtered_shopping_ads += 1
                                filtered_ads.append(ad)
            else:
                filtered_ads = ads

            shopping_ad_links = []

            for ad in filtered_ads:
                ad_link = ad[1]
                ad_title = ad[2].replace("\n", " ")
                ad_target_link = ad[3]
                ad_position = ad[4]
                logger.debug(f"Ad title: {ad_title}, Ad link: {ad_link}")

                if self._exclude_list:
                    for exclude_item in self._exclude_list:
                        if (
                            exclude_item in ad_target_link
                            or exclude_item.lower() in ad_title.lower()
                        ):
                            logger.debug(f"Excluding [{ad_title}]: {ad_target_link}")
                            self._stats.num_excluded_shopping_ads += 1
                            break
                    else:
                        logger.info("======= Found a Shopping Ad =======")
                        shopping_ad_links.append((ad[0], ad_link, ad_title, ad_position))
                else:
                    logger.info("======= Found a Shopping Ad =======")
                    shopping_ad_links.append((ad[0], ad_link, ad_title, ad_position))

            return shopping_ad_links

        except NoSuchElementException:
            logger.info("No shopping ads are shown!")
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("shopping_ad_scan", exp)
            raise

        return ads

    def _get_ad_links(self) -> AdList:
        """Extract ad links to click

        :rtype: AdList
        :returns: List of (ad, ad_link, ad_title) tuples
        """

        logger.info("Getting ad links...")
        try:
            ads = []

            scroll_count = 0

            logger.debug(f"Max scroll limit: {self._max_scroll_limit}")

            while not self._is_scroll_at_the_end():
                try:
                    top_ads_containers = self._driver.find_elements(*self.TOP_ADS_CONTAINER)
                    for ad_container in top_ads_containers:
                        ads.extend(ad_container.find_elements(*self.AD_RESULTS))

                except NoSuchElementException:
                    logger.debug("Could not found top ads!")

                try:
                    bottom_ads_containers = self._driver.find_elements(*self.BOTTOM_ADS_CONTAINER)
                    for ad_container in bottom_ads_containers:
                        ads.extend(ad_container.find_elements(*self.AD_RESULTS))

                except NoSuchElementException:
                    logger.debug("Could not found bottom ads!")

                if self._max_scroll_limit > 0:
                    if scroll_count == self._max_scroll_limit:
                        logger.debug("Reached to max scroll limit! Ending scroll...")
                        break

                self._driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
                sleep(get_random_sleep(2, 2.5) * config.behavior.wait_factor)

                scroll_count += 1

            if not ads:
                return []

            # clean non-ad links and duplicates
            cleaned_ads = []
            links = []

            for ad in ads:
                if ad.get_attribute("data-pcu"):
                    ad_link = ad.get_attribute("href")

                    if ad_link not in links:
                        links.append(ad_link)
                        cleaned_ads.append(ad)
            ad_positions = {id(ad): position for position, ad in enumerate(cleaned_ads, start=1)}

            self._stats.ads_found = len(cleaned_ads)

            # if there are filter words given, filter results accordingly
            filtered_ads = []

            if self._filter_words:
                for ad in cleaned_ads:
                    ad_title = self._extract_ad_title(ad).lower()
                    ad_link = ad.get_attribute("data-pcu")

                    logger.debug(f"data-pcu ad_link: {ad_link}")

                    for word in self._filter_words:
                        if word in ad_link or word in ad_title:
                            if ad not in filtered_ads:
                                logger.debug(f"Filtering [{ad_title}]: {ad_link}")
                                self._stats.num_filtered_ads += 1
                                filtered_ads.append(ad)
            else:
                filtered_ads = cleaned_ads

            ad_links = []

            for ad in filtered_ads:
                ad_link = ad.get_attribute("href")
                ad_target_link = ad.get_attribute("data-pcu") or ad_link
                ad_title = self._extract_ad_title(ad)
                ad_position = ad_positions.get(id(ad))
                logger.debug(f"Ad title: {ad_title}, Ad link: {ad_link}")

                if self._ad_allowlist:
                    if not any(
                        domain_matches_url(domain, ad_target_link)
                        for domain in self._ad_allowlist
                    ):
                        logger.debug(
                            f"Skipping [{ad_title}] because it is not in ad_allowlist: "
                            f"{ad_target_link}"
                        )
                        self._stats.num_filtered_ads += 1
                        continue

                if self._ad_denylist:
                    if any(
                        domain_matches_url(domain, ad_target_link)
                        for domain in self._ad_denylist
                    ):
                        logger.debug(
                            f"Skipping [{ad_title}] because it is in ad_denylist: "
                            f"{ad_target_link}"
                        )
                        self._stats.num_excluded_ads += 1
                        continue

                if self._exclude_list:
                    for exclude_item in self._exclude_list:
                        if (
                            exclude_item in ad_target_link
                            or exclude_item.lower() in ad_title.lower()
                        ):
                            logger.debug(f"Excluding [{ad_title}]: {ad_link}")
                            self._stats.num_excluded_ads += 1
                            break
                    else:
                        logger.info("======= Found an Ad =======")
                        ad_links.append((ad, ad_link, ad_title, ad_position))
                else:
                    logger.info("======= Found an Ad =======")
                    ad_links.append((ad, ad_link, ad_title, ad_position))

            return ad_links
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("ad_scan", exp)
            raise

    def _get_non_ad_links(
        self, ad_links: AdList, non_ad_domains: Optional[list[str]] = None
    ) -> NonAdList:
        """Extract non-ad link elements

        :type ad_links: AdList
        :param ad_links: List of ad links found to exclude
        :type non_ad_domains: list
        :param non_ad_domains: List of domains to select for non-ad links
        :rtype: NonAdList
        :returns: List of non-ad link elements
        """

        logger.info("Getting non-ad links...")
        try:
            # go to top of the page
            self._driver.find_element(By.TAG_NAME, "body").send_keys(Keys.HOME)

            all_links = self._driver.find_elements(*self.ALL_LINKS)

            logger.debug(f"len(all_links): {len(all_links)}")

            non_ad_links = []

            for link in all_links:
                for ad in ad_links:
                    if link == ad[0]:
                        # skip ad element
                        break
                else:
                    link_url = link.get_attribute("href")
                    if (
                        link_url
                        and (
                            link.get_attribute("role")
                            not in (
                                "link",
                                "button",
                                "menuitem",
                                "menuitemradio",
                            )
                        )
                        and link.get_attribute("jsname")
                        and link.get_attribute("data-ved")
                        and not link.get_attribute("data-rw")
                        and "/maps" not in link_url
                        and "/search?q" not in link_url
                        and "googleadservices" not in link_url
                        and "https://www.google" not in link_url
                        and (link_url and link_url.startswith("http"))
                        and len(link.find_elements(By.TAG_NAME, "svg")) == 0
                    ):
                        if non_ad_domains:
                            logger.debug(f"Evaluating [{link_url}] to add as non-ad link...")

                            for domain in non_ad_domains:
                                if domain in link_url:
                                    logger.debug(f"Adding [{link_url}] to non-ad links")
                                    non_ad_links.append(link)
                                    break
                        else:
                            logger.debug(f"Adding [{link_url}] to non-ad links")
                            non_ad_links.append(link)

            logger.info(f"Found {len(non_ad_links)} non-ad links")

            # if there is no domain to filter, randomly select 3 links
            if not non_ad_domains and len(non_ad_links) > 3:
                logger.info("Randomly selecting 3 from non-ad links...")
                non_ad_links = random.sample(non_ad_links, k=3)

            return non_ad_links
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("non_ad_scan", exp)
            raise

    @staticmethod
    def _normalize_ui_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "")
        without_accents = "".join(
            character for character in normalized if not unicodedata.combining(character)
        )
        return " ".join(without_accents.lower().split())

    @staticmethod
    def _is_browser_session_unavailable_exception(exp: Exception) -> bool:
        message = str(exp).lower()
        return any(
            marker in message
            for marker in (
                "invalid session id",
                "tab crashed",
                "disconnected",
                "connection refused",
                "connection aborted",
                "remote end closed connection",
                "failed to establish a new connection",
            )
        )

    def _abort_due_to_browser_unavailable(self, stage: str, exp: Exception) -> None:
        logger.error(
            f"Browser session became unavailable during {stage}. "
            "Stopping this run cleanly."
        )
        logger.debug(f"Browser-unavailable exception at {stage}: {exp}")
        try:
            self._save_step_screenshot(f"{stage}_browser_unavailable")
        except Exception:
            pass
        try:
            self._driver.quit()
        except Exception:
            pass
        raise BrowserSessionUnavailableError(str(exp)) from exp

    def _collect_element_ui_strings(
        self, element: selenium.webdriver.remote.webelement.WebElement
    ) -> list[str]:
        values: list[str] = []
        for attribute_name in ("aria-label", "title", "value", "id", "name", "class"):
            try:
                attribute_value = element.get_attribute(attribute_name)
            except StaleElementReferenceException:
                return []
            if attribute_value:
                values.append(attribute_value)

        try:
            text_value = element.text
        except StaleElementReferenceException:
            return values
        if text_value:
            values.append(text_value)

        normalized_values: list[str] = []
        for value in values:
            normalized = self._normalize_ui_text(value)
            if normalized and normalized not in normalized_values:
                normalized_values.append(normalized)

        return normalized_values

    def _iter_visible_button_candidates(self):
        seen_ids: set[str] = set()

        for selector in self.BUTTON_CANDIDATE_SELECTORS:
            try:
                candidates = self._driver.find_elements(*selector)
            except Exception as exp:
                if self._is_browser_session_unavailable_exception(exp):
                    self._abort_due_to_browser_unavailable("button_candidate_scan", exp)
                raise

            for candidate in candidates:
                candidate_id = getattr(candidate, "id", None)
                if candidate_id and candidate_id in seen_ids:
                    continue
                if candidate_id:
                    seen_ids.add(candidate_id)

                try:
                    if not candidate.is_displayed() or not candidate.is_enabled():
                        continue
                except StaleElementReferenceException:
                    continue
                except Exception as exp:
                    if self._is_browser_session_unavailable_exception(exp):
                        self._abort_due_to_browser_unavailable(
                            "button_candidate_visibility_check",
                            exp,
                        )
                    raise

                yield candidate

    def _find_best_button_candidate(
        self,
        positive_phrases: tuple[str, ...],
        *,
        negative_phrases: tuple[str, ...] = (),
    ) -> Optional[selenium.webdriver.remote.webelement.WebElement]:
        normalized_positive = tuple(self._normalize_ui_text(phrase) for phrase in positive_phrases)
        normalized_negative = tuple(self._normalize_ui_text(phrase) for phrase in negative_phrases)
        best_candidate = None
        best_score = 0

        for candidate in self._iter_visible_button_candidates():
            ui_strings = self._collect_element_ui_strings(candidate)
            if not ui_strings:
                continue

            combined_text = " | ".join(ui_strings)
            if any(negative_phrase and negative_phrase in combined_text for negative_phrase in normalized_negative):
                continue

            score = 0
            for positive_phrase in normalized_positive:
                if not positive_phrase:
                    continue
                for ui_string in ui_strings:
                    if ui_string == positive_phrase:
                        score = max(score, 100 + len(positive_phrase))
                    elif positive_phrase in ui_string:
                        score = max(score, len(positive_phrase))

            if score > best_score:
                best_candidate = candidate
                best_score = score

        return best_candidate

    def _click_ui_element(
        self,
        element: selenium.webdriver.remote.webelement.WebElement,
        *,
        stage: str,
    ) -> None:
        try:
            self._driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                element,
            )
            sleep(get_random_sleep(0.2, 0.5) * config.behavior.wait_factor)
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable(stage, exp)

        try:
            element.click()
        except ElementClickInterceptedException:
            try:
                self._driver.execute_script("arguments[0].click();", element)
            except Exception as exp:
                if self._is_browser_session_unavailable_exception(exp):
                    self._abort_due_to_browser_unavailable(stage, exp)
                raise
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable(stage, exp)
            raise

    def _page_has_google_consent_surface(self) -> bool:
        current_url = (self._driver.current_url or "").lower()
        if "consent.google" in current_url or "consent.youtube" in current_url:
            return True

        try:
            policy_links = self._driver.find_elements(By.CSS_SELECTOR, "a[href*='policies.google']")
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("consent_surface_detection", exp)
            raise

        return bool(policy_links)

    def _find_interactable_search_input(
        self, timeout: int = 0
    ) -> Optional[selenium.webdriver.remote.webelement.WebElement]:
        def _locate(_driver):
            for element in self._driver.find_elements(*self.SEARCH_INPUT):
                try:
                    if element.is_displayed() and element.is_enabled():
                        return element
                except StaleElementReferenceException:
                    continue
            return False

        if timeout <= 0:
            located = _locate(None)
            return located or None

        try:
            return WebDriverWait(self._driver, timeout).until(_locate)
        except TimeoutException:
            return None

    def _submit_search_query(self) -> bool:
        search_input_box = self._find_interactable_search_input(timeout=3)
        if not search_input_box:
            logger.debug("Search input is not visible and interactable.")
            return False

        try:
            self._driver.execute_script("arguments[0].focus();", search_input_box)
            search_input_box.click()
            self._type_humanlike(search_input_box, self._search_query)
            return True
        except (ElementNotInteractableException, StaleElementReferenceException) as exp:
            logger.debug(f"Search input could not be used for typing: {exp}")
            return False
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("search_query_submission", exp)
            logger.debug(f"Search query submission failed: {exp}")
            return False

    def _close_cookie_dialog(self) -> bool:
        """If cookie dialog is opened, close it by accepting"""

        logger.debug("Waiting for cookie dialog...")

        sleep(get_random_sleep(3, 3.5) * config.behavior.wait_factor)

        try:
            consent_surface_present = self._page_has_google_consent_surface()
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("cookie_dialog_detection", exp)
            raise

        if not consent_surface_present:
            logger.debug("No cookie dialog found! Continue with search...")
            return False

        consent_handled = False

        for attempt in range(3):
            button = self._find_best_button_candidate(
                self.COOKIE_CONSENT_ACTION_PHRASES,
                negative_phrases=self.UNRELATED_UI_BUTTON_PHRASES,
            )
            if not button:
                if not consent_handled:
                    logger.debug("No recognizable cookie consent action button was found.")
                break

            try:
                logger.debug(f"Clicking button {button.get_attribute('outerHTML')}")
            except Exception:
                logger.debug("Clicking cookie consent action button.")

            try:
                self._click_ui_element(button, stage=f"cookie_dialog_click_{attempt + 1}")
            except (
                ElementNotInteractableException,
                ElementClickInterceptedException,
                StaleElementReferenceException,
            ) as exp:
                logger.debug(f"Cookie consent button interaction failed: {exp}")
                continue

            consent_handled = True
            sleep(get_random_sleep(1, 1.5) * config.behavior.wait_factor)
            self._wait_for_page_settle(timeout=4)

            if not self._page_has_google_consent_surface():
                break

        return consent_handled

    def _is_scroll_at_the_end(self) -> bool:
        """Check if scroll is at the end

        :rtype: bool
        :returns: Whether the scrollbar was reached to end or not
        """

        page_height = self._driver.execute_script("return document.body.scrollHeight;")
        total_scrolled_height = self._driver.execute_script(
            "return window.pageYOffset + window.innerHeight;"
        )

        return page_height - 1 <= total_scrolled_height

    def _delete_cache_and_cookies(self) -> None:
        """Delete browser cache, storage, and cookies"""

        logger.debug(f"Applying browser cleanup policy: {self._profile_cleanup_policy}")

        try:
            if self._profile_cleanup_policy in ("ephemeral", "city_profile_recycle"):
                self._driver.delete_all_cookies()
                self._driver.execute_cdp_cmd("Network.clearBrowserCache", {})
                self._driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
                self._driver.execute_script("window.localStorage.clear();")
                self._driver.execute_script("window.sessionStorage.clear();")
                return

            if self._profile_cleanup_policy == "city_profile_ip_changed_cleanup":
                self._open_google_surface_for_profile_ops()
                for cookie in self._driver.get_cookies():
                    cookie_name = str(cookie.get("name") or "").strip()
                    if cookie_name in self._profile_preserve_cookie_names:
                        continue
                    try:
                        self._driver.delete_cookie(cookie_name)
                    except Exception as exp:
                        logger.debug(
                            f"Failed to delete cookie '{cookie_name}' during profile cleanup: {exp}"
                        )
                self._driver.execute_cdp_cmd("Network.clearBrowserCache", {})
                self._driver.execute_script("window.localStorage.clear();")
                self._driver.execute_script("window.sessionStorage.clear();")
                return

            if self._profile_cleanup_policy == "city_profile_soft_cleanup":
                self._driver.execute_cdp_cmd("Network.clearBrowserCache", {})
                self._driver.execute_script("window.sessionStorage.clear();")
                return

        except Exception as exp:
            if "not connected to DevTools" in str(exp):
                logger.debug("Incognito mode is active. No need to delete cache. Skipping...")

    def _results_page_ready(self) -> bool:
        for selector in self.RESULTS_READY_SELECTORS:
            try:
                if self._driver.find_elements(*selector):
                    return True
            except Exception as exp:
                if self._is_browser_session_unavailable_exception(exp):
                    self._abort_due_to_browser_unavailable("results_ready_probe", exp)
                return False

        try:
            current_url = (self._driver.current_url or "").lower()
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("results_ready_url_probe", exp)
            return False
        return "/search?" in current_url or "&q=" in current_url

    def _open_search_results_directly(self) -> None:
        """Fallback to direct Google search URL when homepage input is unavailable."""

        query_param = urllib.parse.quote_plus(self._search_query)
        search_url = f"{self.URL}/search?q={query_param}"
        logger.info(f"Opening direct search URL: {search_url}")
        self._driver.get(search_url)
        self._wait_for_page_settle()

    def _ensure_browser_session_alive(self, stage: str) -> None:
        try:
            self._driver.execute_script("return document.readyState")
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable(stage, exp)
            raise

    def _page_has_captcha_indicators(self) -> bool:
        try:
            current_url = (self._driver.current_url or "").lower()
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("captcha_url_probe", exp)
            raise

        if any(marker in current_url for marker in self.CAPTCHA_URL_MARKERS):
            return True

        try:
            page_text = (self._driver.page_source or "").lower()
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("captcha_page_source_probe", exp)
            raise

        return any(
            marker in page_text
            for marker in (
                "g-recaptcha",
                "data-sitekey",
                "captcha-dialog",
                *[marker.lower() for marker in self.BLOCK_PAGE_MARKERS],
            )
        )

    def _find_captcha_container(self) -> Optional[selenium.webdriver.remote.webelement.WebElement]:
        for selector in (self.CAPTCHA_SITEKEY, self.RECAPTCHA):
            try:
                elements = self._driver.find_elements(*selector)
            except Exception as exp:
                if self._is_browser_session_unavailable_exception(exp):
                    self._abort_due_to_browser_unavailable("captcha_element_probe", exp)
                raise

            for element in elements:
                try:
                    if element.is_displayed():
                        return element
                except StaleElementReferenceException:
                    continue
                except Exception as exp:
                    if self._is_browser_session_unavailable_exception(exp):
                        self._abort_due_to_browser_unavailable(
                            "captcha_element_visibility_probe",
                            exp,
                        )
                    raise

            if elements:
                return elements[0]

        return None

    def _wait_for_page_settle(self, timeout: int = 8) -> None:
        """Give Google a chance to finish first paint/load before probing the page."""

        try:
            WebDriverWait(self._driver, timeout=timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            logger.debug("Page settle wait timed out. Continuing with best-effort state.")

        sleep(get_random_sleep(1.2, 2.2) * config.behavior.wait_factor)

    def _set_start_url(self, country_code: str) -> None:
        """Set start url according to country code of the proxy IP

        :type country_code: str
        :param country_code: Country code for the proxy IP
        """

        with open("domain_mapping.json", "r") as domains_file:
            domains = json.load(domains_file)

        country_domain = domains.get(country_code, "www.google.com")
        self.URL = f"https://{country_domain}"

        logger.debug(f"Start url was set to {self.URL}")

    def _make_random_scrolls(self) -> None:
        """Make random scrolls on page"""

        logger.debug("Making random scrolls...")

        directions = [Direction.DOWN]
        directions += random.choices(
            [Direction.UP] * 5 + [Direction.DOWN] * 5, k=random.choice(range(1, 5))
        )

        logger.debug(f"Direction choices: {[d.value for d in directions]}")

        for direction in directions:
            try:
                if direction == Direction.DOWN and not self._is_scroll_at_the_end():
                    scroll_y = random.choice(range(500, 900))
                    self._driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_y)
                elif direction == Direction.UP:
                    scroll_y = -random.choice(range(350, 700))
                    self._driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_y)
            except Exception as exp:
                logger.debug(f"Skipping random scroll step due to browser instability: {exp}")
                return

            sleep(get_random_sleep(1, 3) * config.behavior.wait_factor)

        try:
            self._driver.execute_script("window.scrollTo(0, 0);")
        except Exception as exp:
            logger.debug(f"Skipping final scroll-to-top due to browser instability: {exp}")

    def _make_random_swipes(self) -> None:
        """Make random swipes on page"""

        logger.debug("Making random swipes...")

        directions = [Direction.DOWN, Direction.DOWN]
        directions += random.choices(
            [Direction.UP] * 5 + [Direction.DOWN] * 5, k=random.choice(range(1, 5))
        )

        logger.debug(f"Direction choices: {[d.value for d in directions]}")

        for direction in directions:
            if direction == Direction.DOWN:
                self._send_swipe(direction=Direction.DOWN)

            elif direction == Direction.UP:
                self._send_swipe(direction=Direction.UP)

            sleep(get_random_sleep(1, 2) * config.behavior.wait_factor)

        HOME_KEYCODE = 122
        adb_controller.send_keyevent(HOME_KEYCODE)  # go to top by sending Home key

    def _send_swipe(self, direction: Direction) -> None:
        """Send swipe action to mobile device

        :type direction: Direction
        :param direction: Direction to swipe
        """

        x_position = random.choice(range(100, 200))
        duration = random.choice(range(100, 500))

        if direction == Direction.DOWN:
            y_start_position = random.choice(range(1000, 1500))
            y_end_position = random.choice(range(500, 1000))

        elif direction == Direction.UP:
            y_start_position = random.choice(range(500, 1000))
            y_end_position = random.choice(range(1000, 1500))

        adb_controller.send_swipe(
            x1=x_position,
            y1=y_start_position,
            x2=x_position,
            y2=y_end_position,
            duration=duration,
        )

    def _make_random_mouse_movements(self) -> None:
        """Make random mouse movements"""

        if self._random_mouse_enabled:
            pyautogui = None
            screen_width = screen_height = None
            try:
                import pyautogui

                logger.debug("Making random mouse movements...")

                screen_width, screen_height = pyautogui.size()
                pyautogui.moveTo(screen_width / 2 - 300, screen_height / 2 - 200)

                logger.debug(pyautogui.position())

                ease_methods = [
                    pyautogui.easeInQuad,
                    pyautogui.easeOutQuad,
                    pyautogui.easeInOutQuad,
                ]

                logger.debug("Going LEFT and DOWN...")

                pyautogui.move(
                    -random.choice(range(200, 300)),
                    random.choice(range(250, 450)),
                    1,
                    random.choice(ease_methods),
                )

                logger.debug(pyautogui.position())

                for _ in range(1, random.choice(range(3, 7))):
                    direction = random.choice(list(Direction))
                    ease_method = random.choice(ease_methods)

                    logger.debug(f"Going {direction.value}...")

                    if direction == Direction.LEFT:
                        pyautogui.move(-(random.choice(range(100, 200))), 0, 0.5, ease_method)

                    elif direction == Direction.RIGHT:
                        pyautogui.move(random.choice(range(200, 400)), 0, 0.3, ease_method)

                    elif direction == Direction.UP:
                        pyautogui.move(0, -(random.choice(range(100, 200))), 1, ease_method)
                        pyautogui.scroll(random.choice(range(1, 7)))

                    elif direction == Direction.DOWN:
                        pyautogui.move(0, random.choice(range(150, 300)), 0.7, ease_method)
                        pyautogui.scroll(-random.choice(range(1, 7)))

                    else:
                        pyautogui.move(
                            random.choice(range(100, 200)),
                            random.choice(range(150, 250)),
                            1,
                            ease_method,
                        )

                    logger.debug(pyautogui.position())

            except pyautogui.FailSafeException:
                logger.debug("The mouse cursor was moved to one of the screen corners!")

                pyautogui.FAILSAFE = False

                logger.debug("Moving cursor to center...")
                pyautogui.moveTo(screen_width / 2, screen_height / 2)
            except Exception as exp:
                logger.debug(f"Skipping random mouse movements: {exp}")

    def _check_captcha(self) -> None:
        """Check if captcha exists and solve it if 2captcha is used, otherwise exit"""

        sleep(get_random_sleep(1, 1.5) * config.behavior.wait_factor)
        try:
            WebDriverWait(self._driver, timeout=5).until(
                lambda driver: driver.execute_script("return document.readyState") in ("interactive", "complete")
            )
        except Exception:
            logger.debug("Page readiness check timed out before captcha probe.")

        try:
            if not self._page_has_captcha_indicators():
                logger.debug("No captcha indicators seen. Continue to search...")
                return

            captcha = self._find_captcha_container()
            if not captcha:
                logger.debug("Captcha indicators were seen, but no captcha container was found.")
                return

            if captcha:
                logger.error("Captcha was shown.")
                self._save_step_screenshot("captcha_seen")

                if self._hooks_enabled:
                    hooks.captcha_seen_hook(self._driver)

                self._stats.captcha_seen = True
                self._record_proxy_ip_checkpoint("captcha_seen")

                if not self._twocaptcha_apikey:
                    logger.info("Please try with a different proxy or enable 2captcha service.")
                    logger.info(self.stats)
                    raise SystemExit()

                max_captcha_attempts = 2
                for attempt_index in range(max_captcha_attempts):
                    if attempt_index > 0:
                        logger.info(
                            "Retrying captcha in the same browser session with a refreshed page."
                        )
                        self._save_step_screenshot(f"captcha_retry_refresh_{attempt_index:02d}")
                        self._driver.refresh()
                        sleep(get_random_sleep(3, 4) * config.behavior.wait_factor)
                        captcha = self._find_captcha_container()
                        if not captcha:
                            logger.warning(
                                "Captcha container disappeared after refresh retry. "
                                "Continuing with post-refresh page state."
                            )
                            return

                    cookies = ";".join(
                        [f"{cookie['name']}:{cookie['value']}" for cookie in self._driver.get_cookies()]
                    )
                    browser_user_agent = self._driver.execute_script("return navigator.userAgent")

                    logger.debug(f"Cookies: {cookies}")

                    sitekey = captcha.get_attribute("data-sitekey")
                    data_s = captcha.get_attribute("data-s")

                    logger.debug(f"data-sitekey: {sitekey}, data-s: {data_s}")
                    logger.info(
                        "Captcha fingerprint: "
                        f"attempt={attempt_index + 1}/{max_captcha_attempts}, "
                        f"url={self._driver.current_url}, "
                        f"sitekey={sitekey}, "
                        f"has_data_s={bool(data_s)}, "
                        f"cookie_count={len(self._driver.get_cookies())}, "
                        f"has_proxy={bool(getattr(self._driver, '_active_proxy', None))}, "
                        f"proxy={getattr(self._driver, '_active_proxy', None)}, "
                        f"user_agent={browser_user_agent}"
                    )
                    self._save_step_screenshot(
                        f"captcha_before_solve_attempt_{attempt_index + 1:02d}"
                    )

                    response_code = solve_recaptcha(
                        apikey=self._twocaptcha_apikey,
                        sitekey=sitekey,
                        current_url=self._driver.current_url,
                        data_s=data_s,
                        cookies=cookies,
                        poll_hook=self._on_captcha_poll,
                        proxy=getattr(self._driver, "_active_proxy", None),
                        user_agent=browser_user_agent,
                    )

                    if response_code:
                        logger.info("2captcha returned a captcha token.")
                        self._stats.captcha_token_received = True

                        self._apply_captcha_solution(response_code)
                        self._stats.captcha_token_applied = True
                        logger.info("Captcha token was applied to the page.")
                        self._record_proxy_ip_checkpoint("post_captcha_token_applied")

                        sleep(get_random_sleep(2, 2.5) * config.behavior.wait_factor)
                        self._save_step_screenshot("captcha_after_solve")
                        self._mark_captcha_outcome()
                        self._abort_if_google_blocked("post_captcha")
                        break

                    if attempt_index + 1 < max_captcha_attempts:
                        logger.info(
                            "No captcha token was obtained. Refreshing for one soft retry "
                            "to fetch a fresh Google challenge."
                        )
                        continue

                    logger.info("No captcha token could be obtained. Please try with a different proxy.")
                    self._save_step_screenshot("captcha_unsolved")
                    self._driver.quit()
                    raise SystemExit()

        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("check_captcha", exp)
            if isinstance(exp, NoSuchElementException):
                logger.debug("No captcha seen. Continue to search...")
                return
            raise

    def _is_google_block_page(self) -> bool:
        try:
            page_text = (self._driver.page_source or "").lower()
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("google_block_detection", exp)
            raise
        return all(marker.lower() in page_text for marker in self.BLOCK_PAGE_MARKERS)

    def _abort_if_google_blocked(self, stage: str) -> None:
        if not self._is_google_block_page():
            return

        self._stats.google_blocked_after_captcha = True
        self._save_step_screenshot(f"{stage}_google_blocked")
        logger.error(
            "Google is still blocking this session after captcha handling. "
            "The proxy/session reputation is being rejected."
        )
        logger.info("Please try with a different proxy.")
        self._driver.quit()
        raise SystemExit()

    def _mark_captcha_outcome(self) -> None:
        if self._is_google_block_page():
            self._stats.google_blocked_after_captcha = True
            self._stats.captcha_accepted = False
            logger.warning(
                "Captcha token was received and applied, but Google still rejected the session."
            )
            return

        remaining_captcha = self._find_captcha_container()
        if remaining_captcha:
            self._stats.captcha_accepted = False
            logger.warning("Captcha token was applied, but the captcha challenge is still present.")
        else:
            self._stats.captcha_accepted = True
            logger.info("Captcha challenge cleared and Google accepted the session.")

    def _apply_captcha_solution(self, response_code: str) -> None:
        """Inject the 2captcha token into the current page and submit if needed."""

        logger.debug(f"Applying captcha solution on URL: {self._driver.current_url}")

        apply_result = self._driver.execute_script(
            """
            const token = arguments[0];

            const details = {
                textareasUpdated: 0,
                callbackInvoked: false,
                formSubmitted: false,
                submitClicked: false,
                textareaPresent: false,
            };

            const selectors = [
                'textarea[name="g-recaptcha-response"]',
                'textarea#g-recaptcha-response',
                'input[name="g-recaptcha-response"]',
            ];

            let fields = [];
            for (const selector of selectors) {
                fields = fields.concat(Array.from(document.querySelectorAll(selector)));
            }

            if (!fields.length) {
                const hostForm =
                    document.querySelector('#recaptcha')?.closest('form') ||
                    document.querySelector('form');
                const textarea = document.createElement('textarea');
                textarea.name = 'g-recaptcha-response';
                textarea.id = 'g-recaptcha-response';
                textarea.style.display = 'none';
                (hostForm || document.body).appendChild(textarea);
                fields.push(textarea);
            }

            details.textareaPresent = fields.length > 0;

            for (const field of fields) {
                field.value = token;
                field.innerHTML = token;
                field.dispatchEvent(new Event('input', { bubbles: true }));
                field.dispatchEvent(new Event('change', { bubbles: true }));
                details.textareasUpdated += 1;
            }

            const cfg = window.___grecaptcha_cfg;
            if (cfg && cfg.clients) {
                const visit = (node) => {
                    if (!node || details.callbackInvoked) return;
                    if (typeof node === 'function') {
                        try {
                            node(token);
                            details.callbackInvoked = true;
                            return;
                        } catch (err) {}
                    }
                    if (typeof node !== 'object') return;
                    for (const value of Object.values(node)) {
                        if (details.callbackInvoked) return;
                        visit(value);
                    }
                };
                visit(cfg.clients);
            }

            const form =
                document.querySelector('#recaptcha')?.closest('form') ||
                document.querySelector('textarea[name="g-recaptcha-response"]')?.closest('form') ||
                document.querySelector('form[action*="sorry"]') ||
                document.querySelector('form');

            if (form && !details.callbackInvoked) {
                try {
                    if (typeof form.submit === 'function') {
                        form.submit();
                        details.formSubmitted = true;
                    }
                } catch (err) {}
            }

            if (!details.formSubmitted) {
                const submitButton =
                    document.querySelector('button[type="submit"]') ||
                    document.querySelector('input[type="submit"]') ||
                    document.querySelector('#recaptcha ~ div button');

                if (submitButton) {
                    try {
                        submitButton.click();
                        details.submitClicked = true;
                    } catch (err) {}
                }
            }

            return details;
            """,
            response_code,
        )

        logger.debug(f"Captcha solution apply result: {apply_result}")

        current_url = self._driver.current_url
        wait = WebDriverWait(self._driver, timeout=12)
        try:
            wait.until(lambda driver: "sorry" not in driver.current_url.lower())
            logger.debug("Captcha page redirect detected after token injection.")
            return
        except TimeoutException:
            logger.debug("Captcha page did not redirect after token injection.")

        try:
            wait.until_not(EC.presence_of_element_located(self.RECAPTCHA))
            logger.debug("Captcha element disappeared after token injection.")
            return
        except TimeoutException:
            logger.debug("Captcha element still present after token injection.")

        if "g-recaptcha-response=" not in current_url:
            joiner = "&" if "?" in current_url else "?"
            fallback_url = f"{current_url}{joiner}g-recaptcha-response={response_code}"
            logger.debug("Falling back to URL token append for captcha response.")
            self._driver.get(fallback_url)

    def _close_choose_location_popup(self) -> None:
        """Close 'Choose location for search results' popup"""

        try:
            estimated_loc_images = self._driver.find_elements(*self.ESTIMATED_LOC_IMG)
            if estimated_loc_images:
                estimated_loc_img = estimated_loc_images[0]
                logger.debug(estimated_loc_img.get_attribute("outerHTML"))
                logger.debug("Closing location choose dialog...")
                self._click_ui_element(estimated_loc_img, stage="location_dialog_image")

                sleep(get_random_sleep(1, 1.5) * config.behavior.wait_factor)

                continue_button = self._find_best_button_candidate(
                    self.LOCATION_CONTINUE_ACTION_PHRASES,
                    negative_phrases=self.UNRELATED_UI_BUTTON_PHRASES,
                )
                if continue_button:
                    logger.debug(continue_button.get_attribute("outerHTML"))
                    self._click_ui_element(
                        continue_button,
                        stage="location_dialog_continue",
                    )
                    sleep(get_random_sleep(0.1, 0.5) * config.behavior.wait_factor)
                    return

            sleep(get_random_sleep(1, 1.5) * config.behavior.wait_factor)

            logger.debug("Checking alternative location dialog...")
            logger.debug("Closing location choose dialog by selecting Not now...")

            not_now_button = self._find_best_button_candidate(
                self.LOCATION_DISMISS_ACTION_PHRASES,
                negative_phrases=self.UNRELATED_UI_BUTTON_PHRASES,
            )
            if not not_now_button:
                logger.debug("No location choose dialog seen. Continue to search...")
                return

            logger.debug(not_now_button.get_attribute("outerHTML"))
            self._click_ui_element(not_now_button, stage="location_dialog_not_now")
            sleep(get_random_sleep(0.2, 0.5) * config.behavior.wait_factor)

        except ElementNotInteractableException:
            logger.debug("Location dialog button element is not interactable!")
        except Exception as exp:
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("close_choose_location_popup", exp)
            raise

        finally:
            # if no not now or continue button exists, send ESC to page to close the dialog
            try:
                self._driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except NoSuchElementException:
                pass
            except Exception as exp:
                if self._is_browser_session_unavailable_exception(exp):
                    self._abort_due_to_browser_unavailable(
                        "close_choose_location_popup_escape",
                        exp,
                    )
                raise

    def _type_humanlike(
        self, element: selenium.webdriver.remote.webelement.WebElement, text: str
    ) -> None:
        """Type text slowly like a human

        :type element: selenium.webdriver.remote.webelement.WebElement
        :param element: Element to type into
        :type text: str
        :param text: Text to type
        """

        try:
            element.clear()
        except Exception:
            pass

        try:
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.BACKSPACE)
        except Exception:
            pass

        try:
            for character in text:
                element.send_keys(character)
                sleep(get_random_sleep(0.05, 0.15) * config.behavior.wait_factor)

            element.send_keys(Keys.ENTER)

        except Exception as exp:
            logger.debug(f"Error while typing: {exp}")
            if self._is_browser_session_unavailable_exception(exp):
                self._abort_due_to_browser_unavailable("type_search_query", exp)
            raise

    def set_browser_id(self, browser_id: Optional[int] = None) -> None:
        """Set browser id in stats if multiple browsers are used

        :type browser_id: int
        :param browser_id: Browser id to separate instances in log for multiprocess runs
        """

        self._stats.browser_id = browser_id

    def assign_android_device(self, device_id: str) -> None:
        """Assign Android device to browser

        :type device_id: str
        :param device_id: Android device ID to assign
        """

        logger.info(f"Assigning device[{device_id}] to browser {self._stats.browser_id}")

        self._android_device_id = device_id

    @staticmethod
    def _process_query(query: str) -> tuple[str, list[str]]:
        """Extract search query and filter words from the query input

        Query and filter words are splitted with "@" character. Multiple
        filter words can be used by separating with "#" character.

        e.g. wireless keyboard@amazon#ebay
             bluetooth headphones @ sony # amazon  #bose

        :type query: str
        :param query: Query string with optional filter words
        :rtype tuple
        :returns: Search query and list of filter words if any
        """

        search_query = query.split("@")[0].strip()

        filter_words = []

        if "@" in query:
            filter_words = [word.strip().lower() for word in query.split("@")[1].split("#")]

        if filter_words:
            logger.debug(f"Filter words: {filter_words}")

        return (search_query, filter_words)

    @property
    def stats(self) -> SearchStats:
        """Return search statistics data

        :rtype: SearchStats
        :returns: Search statistics data
        """

        return self._stats
