import json
import multiprocessing
from dataclasses import dataclass
from typing import Optional

from logger import logger


@dataclass
class PathParams:
    query_file: str
    proxy_file: str
    user_agents: Optional[str] = "user_agents.txt"
    filtered_domains: Optional[str] = "domains.txt"
    ad_allowlist: Optional[str] = "ad_allowlist.txt"
    ad_denylist: Optional[str] = "ad_denylist.txt"


@dataclass
class WebdriverParams:
    proxy: str
    auth: Optional[bool] = False
    incognito: Optional[bool] = False
    identity_mode: Optional[str] = "legacy"
    country_domain: Optional[bool] = False
    language_from_proxy: Optional[bool] = False
    ss_on_exception: Optional[bool] = False
    window_size: Optional[str] = ""
    shift_windows: Optional[bool] = False
    prefer_headless: Optional[bool] = False
    isolated_chromedriver_per_run: Optional[bool] = False
    use_seleniumbase: Optional[bool] = False


@dataclass
class BehaviorParams:
    query: str
    ad_page_min_wait: Optional[int] = 10
    ad_page_max_wait: Optional[int] = 15
    nonad_page_min_wait: Optional[int] = 15
    nonad_page_max_wait: Optional[int] = 20
    max_scroll_limit: Optional[int] = 0
    check_shopping_ads: Optional[bool] = True
    excludes: Optional[str] = ""
    random_mouse: Optional[bool] = False
    custom_cookies: Optional[bool] = False
    click_order: Optional[int] = 5
    browser_count: Optional[int] = 2
    multiprocess_style: Optional[int] = 1
    loop_wait_time: Optional[int] = 60
    max_concurrent_groups: Optional[int] = 1
    concurrent_group_launch_stagger_seconds: Optional[float] = 8.0
    wait_factor: Optional[float] = 1.0
    running_interval_start: Optional[str] = ""
    running_interval_end: Optional[str] = ""
    twocaptcha_apikey: Optional[str] = ""
    hooks_enabled: Optional[bool] = False
    telegram_enabled: Optional[bool] = False
    send_to_android: Optional[bool] = False
    request_boost: Optional[bool] = False
    no_clickable_ads_retry_probability: Optional[float] = 0.7
    no_clickable_ads_exit_probability: Optional[float] = 0.3
    no_clickable_ads_max_retries: Optional[int] = 1
    enable_v2_enterprise_fallback: Optional[bool] = False


class ConfigReader:
    """Config file reader"""

    def __init__(self) -> None:
        self.paths = None
        self.webdriver = None
        self.behavior = None

    def read_parameters(self) -> None:
        """Read parameters from the config.json file"""

        with open("config.json", encoding="utf-8") as config_file:
            try:
                config = json.loads(config_file.read())
            except Exception:
                logger.error("Failed to read config file. Check format and try again.")
                raise SystemExit()

        self.paths = PathParams(
            query_file=config["paths"]["query_file"],
            proxy_file=config["paths"]["proxy_file"],
            user_agents=config["paths"]["user_agents"],
            filtered_domains=config["paths"]["filtered_domains"],
            ad_allowlist=config["paths"].get("ad_allowlist", "ad_allowlist.txt"),
            ad_denylist=config["paths"].get("ad_denylist", "ad_denylist.txt"),
        )

        if self.paths.proxy_file and config["webdriver"]["proxy"]:
            logger.error("Either 'proxy_file' or 'proxy' parameter should be empty.")
            raise SystemExit()

        self.webdriver = WebdriverParams(
            proxy=config["webdriver"]["proxy"],
            auth=config["webdriver"]["auth"],
            incognito=config["webdriver"]["incognito"],
            identity_mode=config["webdriver"].get("identity_mode", "legacy"),
            country_domain=config["webdriver"]["country_domain"],
            language_from_proxy=config["webdriver"]["language_from_proxy"],
            ss_on_exception=config["webdriver"]["ss_on_exception"],
            window_size=config["webdriver"]["window_size"],
            shift_windows=config["webdriver"]["shift_windows"],
            prefer_headless=config["webdriver"].get("prefer_headless", False),
            isolated_chromedriver_per_run=config["webdriver"].get(
                "isolated_chromedriver_per_run", False
            ),
            use_seleniumbase=config["webdriver"]["use_seleniumbase"],
        )

        if self.paths.query_file and config["behavior"]["query"]:
            logger.error("Either 'query_file' or 'query' parameter should be empty.")
            raise SystemExit()

        browser_count = config["behavior"]["browser_count"]

        self.behavior = BehaviorParams(
            query=config["behavior"]["query"],
            ad_page_min_wait=config["behavior"]["ad_page_min_wait"],
            ad_page_max_wait=config["behavior"]["ad_page_max_wait"],
            nonad_page_min_wait=config["behavior"]["nonad_page_min_wait"],
            nonad_page_max_wait=config["behavior"]["nonad_page_max_wait"],
            max_scroll_limit=config["behavior"]["max_scroll_limit"],
            check_shopping_ads=config["behavior"]["check_shopping_ads"],
            excludes=config["behavior"]["excludes"],
            random_mouse=config["behavior"]["random_mouse"],
            custom_cookies=config["behavior"]["custom_cookies"],
            click_order=config["behavior"]["click_order"],
            browser_count=multiprocessing.cpu_count() if browser_count == 0 else browser_count,
            multiprocess_style=config["behavior"]["multiprocess_style"],
            loop_wait_time=config["behavior"]["loop_wait_time"],
            max_concurrent_groups=config["behavior"].get("max_concurrent_groups", 1),
            concurrent_group_launch_stagger_seconds=config["behavior"].get(
                "concurrent_group_launch_stagger_seconds", 8.0
            ),
            wait_factor=config["behavior"]["wait_factor"],
            running_interval_start=config["behavior"]["running_interval_start"],
            running_interval_end=config["behavior"]["running_interval_end"],
            twocaptcha_apikey=config["behavior"]["2captcha_apikey"],
            hooks_enabled=config["behavior"]["hooks_enabled"],
            telegram_enabled=config["behavior"]["telegram_enabled"],
            send_to_android=config["behavior"]["send_to_android"],
            request_boost=config["behavior"]["request_boost"],
            no_clickable_ads_retry_probability=config["behavior"].get(
                "no_clickable_ads_retry_probability", 0.7
            ),
            no_clickable_ads_exit_probability=config["behavior"].get(
                "no_clickable_ads_exit_probability", 0.3
            ),
            no_clickable_ads_max_retries=config["behavior"].get(
                "no_clickable_ads_max_retries", 1
            ),
            enable_v2_enterprise_fallback=config["behavior"].get(
                "enable_v2_enterprise_fallback", False
            ),
        )


config = ConfigReader()
config.read_parameters()
