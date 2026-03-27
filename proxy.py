import random
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

try:
    from selenium.webdriver import ChromeOptions
except ImportError:
    import sys

    packages_path = Path.cwd() / "env" / "Lib" / "site-packages"
    sys.path.insert(0, f"{packages_path}")

    from selenium.webdriver import ChromeOptions

from config_reader import config
from logger import logger


@dataclass(frozen=True)
class ProxyCredentials:
    host: str
    port: int
    username: str = ""
    password: str = ""
    original_format: str = "host_port"

    @property
    def has_auth(self) -> bool:
        return bool(self.username and self.password)

    @property
    def host_port(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def proxy_url(self) -> str:
        if self.has_auth:
            quoted_username = quote(self.username, safe="")
            quoted_password = quote(self.password, safe="")
            return f"http://{quoted_username}:{quoted_password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"

    @property
    def masked_proxy_url(self) -> str:
        if self.has_auth:
            return (
                f"http://{_mask_secret(self.username)}:{_mask_secret(self.password)}"
                f"@{self.host}:{self.port}"
            )
        return f"http://{self.host}:{self.port}"


def _mask_secret(value: str) -> str:
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def parse_proxy_value(proxy_value: str) -> ProxyCredentials:
    proxy_value = proxy_value.strip().replace("http://", "", 1).replace("https://", "", 1)

    if not proxy_value:
        raise ValueError("Proxy value is empty.")

    if "@" in proxy_value:
        auth_part, server_part = proxy_value.split("@", 1)

        if ":" not in auth_part or ":" not in server_part:
            raise ValueError(
                "Expected authenticated proxy in 'username:password@host:port' format."
            )

        username, password = auth_part.split(":", 1)
        host, port = server_part.rsplit(":", 1)
        original_format = "auth_at"
    else:
        parts = proxy_value.split(":", 3)

        if len(parts) == 4:
            host, port, username, password = parts
            original_format = "host_port_auth"
        elif len(parts) == 2:
            host, port = parts
            username = ""
            password = ""
            original_format = "host_port"
        else:
            raise ValueError(
                "Expected proxy in 'host:port:username:password', "
                "'username:password@host:port', or 'host:port' format."
            )

    if not host or not port:
        raise ValueError("Proxy is missing host or port.")

    try:
        port_number = int(port)
    except ValueError as exc:
        raise ValueError(f"Invalid proxy port: {port}") from exc

    if bool(username) != bool(password):
        raise ValueError("Proxy auth must include both username and password.")

    return ProxyCredentials(
        host=host,
        port=port_number,
        username=username,
        password=password,
        original_format=original_format,
    )


def format_proxy_value(proxy: ProxyCredentials, output_format: str | None = None) -> str:
    output_format = output_format or proxy.original_format

    if output_format == "auth_at":
        if proxy.has_auth:
            return f"{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
        return f"{proxy.host}:{proxy.port}"

    if output_format == "host_port_auth":
        if proxy.has_auth:
            return f"{proxy.host}:{proxy.port}:{proxy.username}:{proxy.password}"
        return f"{proxy.host}:{proxy.port}"

    return f"{proxy.host}:{proxy.port}"


def apply_iproyal_sticky_session(proxy_value: str, lifetime: str = "30m") -> str:
    """Apply sticky-session password suffix for IPRoyal proxies in any accepted format."""

    if not proxy_value:
        return proxy_value

    try:
        proxy = parse_proxy_value(proxy_value)
    except ValueError:
        return proxy_value

    if not proxy.has_auth:
        return proxy_value
    if "iproyal.com" not in proxy.host.lower():
        return proxy_value
    if "_session-" in proxy.password:
        return proxy_value

    session_id = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8))
    sticky_password = f"{proxy.password}_session-{session_id}_lifetime-{lifetime}"
    sticky_proxy = ProxyCredentials(
        host=proxy.host,
        port=proxy.port,
        username=proxy.username,
        password=sticky_password,
        original_format=proxy.original_format,
    )
    logger.debug(
        "Applied sticky proxy session for browser run: "
        f"host={proxy.host_port}, session_id={session_id}, lifetime={lifetime}"
    )
    return format_proxy_value(sticky_proxy)


def extract_proxy_session_id(proxy_value: str) -> str | None:
    if not proxy_value or "_session-" not in proxy_value:
        return None
    try:
        segment = proxy_value.split("_session-", 1)[1]
        return segment.split("_", 1)[0]
    except Exception:
        return None


def get_proxies() -> list[str]:
    """Get proxies from file

    :rtype: list
    :returns: List of proxies
    """

    filepath = Path(config.paths.proxy_file)

    if not filepath.exists():
        raise SystemExit(f"Couldn't find proxy file: {filepath}")

    with open(filepath, encoding="utf-8") as proxyfile:
        proxies = [
            proxy.strip().replace("'", "").replace('"', "")
            for proxy in proxyfile.read().splitlines()
        ]

    return proxies


def install_plugin(
    chrome_options: ChromeOptions,
    proxy_host: str,
    proxy_port: int,
    username: str,
    password: str,
    plugin_folder_name: str,
) -> None:
    """Install plugin on the fly for proxy authentication

    :type chrome_options: ChromeOptions
    :param chrome_options: ChromeOptions instance to add plugin
    :type proxy_host: str
    :param proxy_host: Proxy host
    :type proxy_port: int
    :param proxy_port: Proxy port
    :type username: str
    :param username: Proxy username
    :type password: str
    :param password: Proxy password
    :type plugin_folder_name: str
    :param plugin_folder_name: Plugin folder name for proxy
    """

    manifest_json = """
{
    "version": "1.0.0",
    "manifest_version": 3,
    "name": "Chrome Proxy Authentication",
    "background": {
        "service_worker": "background.js"
    },
    "permissions": [
        "proxy",
        "tabs",
        "unlimitedStorage",
        "storage",
        "webRequest",
        "webRequestAuthProvider"
    ],
    "host_permissions": [
        "<all_urls>"
    ],
    "minimum_chrome_version": "108"
}
"""

    background_js = """
var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "http",
            host: "%s",
            port: %s
        },
        bypassList: ["localhost"]
    }
};
chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            username: "%s",
            password: "%s"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    { urls: ["<all_urls>"] },
    ['blocking']
);
""" % (
        proxy_host,
        proxy_port,
        username,
        password,
    )

    plugins_folder = Path.cwd() / "proxy_auth_plugin"
    plugins_folder.mkdir(exist_ok=True)

    plugin_folder = plugins_folder / plugin_folder_name

    logger.debug(f"Creating '{plugin_folder}' folder...")
    plugin_folder.mkdir(exist_ok=True)

    manifest_path = plugin_folder / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as manifest_file:
        manifest_file.write(manifest_json)

    background_path = plugin_folder / "background.js"
    with open(background_path, "w", encoding="utf-8") as background_js_file:
        background_js_file.write(background_js)

    if not manifest_path.exists() or not background_path.exists():
        raise RuntimeError("Failed to create extension files")

    extension_path = str(plugin_folder.resolve())
    logger.debug(f"Loading extension from: {extension_path}")

    chrome_options.add_argument(f"--load-extension={extension_path}")
