#!/usr/bin/env python3
import argparse
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TEST_URL = "https://ipv4.icanhazip.com"


@dataclass
class ProxyCredentials:
    host: str
    port: int
    username: str
    password: str

    @property
    def proxy_url(self) -> str:
        quoted_username = urllib.parse.quote(self.username, safe="")
        quoted_password = urllib.parse.quote(self.password, safe="")
        return f"http://{quoted_username}:{quoted_password}@{self.host}:{self.port}"

    @property
    def masked_proxy_url(self) -> str:
        return (
            f"http://{mask_secret(self.username)}:{mask_secret(self.password)}"
            f"@{self.host}:{self.port}"
        )


def mask_secret(value: str) -> str:
    if len(value) <= 6:
        return "***"

    return f"{value[:3]}***{value[-3:]}"


def parse_proxy(proxy_value: str) -> ProxyCredentials:
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
    else:
        parts = proxy_value.split(":", 3)

        if len(parts) != 4:
            raise ValueError(
                "Expected proxy in 'host:port:username:password' or "
                "'username:password@host:port' format."
            )

        host, port, username, password = parts

    if not host or not port or not username or not password:
        raise ValueError("Proxy is missing host, port, username, or password.")

    try:
        port_number = int(port)
    except ValueError as exc:
        raise ValueError(f"Invalid proxy port: {port}") from exc

    return ProxyCredentials(
        host=host,
        port=port_number,
        username=username,
        password=password,
    )


def load_proxy_from_file(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Proxy file not found: {path}")

    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned_line = line.strip()
        if cleaned_line:
            return cleaned_line

    raise ValueError(f"Proxy file is empty: {path}")


def test_proxy(
    proxy: ProxyCredentials,
    url: str,
    timeout: float,
    verify_tls: bool,
) -> tuple[str, float]:
    handlers = [urllib.request.ProxyHandler({"http": proxy.proxy_url, "https": proxy.proxy_url})]

    if verify_tls:
        handlers.append(urllib.request.HTTPSHandler())
    else:
        handlers.append(
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
        )

    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(url, headers={"User-Agent": "proxy-checker/1.0"})

    start = time.perf_counter()
    with opener.open(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace").strip()
    elapsed_ms = (time.perf_counter() - start) * 1000

    return body, elapsed_ms


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test an authenticated proxy and print the exit IP."
    )
    parser.add_argument(
        "--proxy",
        help="Proxy string in 'host:port:username:password' or 'username:password@host:port' format.",
    )
    parser.add_argument(
        "--proxy-file",
        default="proxies.txt",
        help="File to read the first non-empty proxy line from when --proxy is omitted.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_TEST_URL,
        help=f"Target URL to request through the proxy. Default: {DEFAULT_TEST_URL}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds. Default: 30",
    )
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        help="Verify upstream TLS certificates. Leave off to mimic curl -k.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        proxy_value = args.proxy or load_proxy_from_file(args.proxy_file)
        proxy = parse_proxy(proxy_value)
        exit_value, elapsed_ms = test_proxy(
            proxy=proxy,
            url=args.url,
            timeout=args.timeout,
            verify_tls=args.verify_tls,
        )
    except Exception as exc:
        print(f"Proxy check failed: {exc}", file=sys.stderr)
        return 1

    print(f"Proxy:    {proxy.masked_proxy_url}")
    print(f"Target:   {args.url}")
    print(f"Exit IP:  {exit_value}")
    print(f"Latency:  {elapsed_ms:.0f} ms")
    print("Status:   OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
