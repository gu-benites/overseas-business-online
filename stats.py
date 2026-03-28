from dataclasses import dataclass


@dataclass
class SearchStats:

    browser_id: int = 0
    initial_proxy_ip: str = ""
    latest_proxy_ip: str = ""
    ip_changed_mid_session: bool = False
    proxy_tunnel_connection_failed: bool = False
    captcha_seen: bool = False
    captcha_token_received: bool = False
    captcha_token_applied: bool = False
    captcha_accepted: bool = False
    google_blocked_after_captcha: bool = False
    ads_found: int = 0
    num_filtered_ads: int = 0
    num_excluded_ads: int = 0
    ads_clicked: int = 0
    non_ads_clicked: int = 0
    shopping_ads_found: int = 0
    num_filtered_shopping_ads: int = 0
    num_excluded_shopping_ads: int = 0
    shopping_ads_clicked: int = 0

    def to_pre_text(self) -> str:
        """Return statistics as pre-formatted fixed-width text

        :rtype: str
        :returns: Statistics as html pre block
        """

        lines = [
            ("Browser ID", self.browser_id) if self.browser_id else None,
            ("Initial Proxy IP", self.initial_proxy_ip) if self.initial_proxy_ip else None,
            ("Latest Proxy IP", self.latest_proxy_ip) if self.latest_proxy_ip else None,
            ("IP Changed Mid-session", "Yes" if self.ip_changed_mid_session else "No"),
            (
                "Proxy Tunnel Failed",
                "Yes" if self.proxy_tunnel_connection_failed else "No",
            ),
            ("Captcha Seen", "Yes" if self.captcha_seen else "No"),
            ("Captcha Token Received", "Yes" if self.captcha_token_received else "No"),
            ("Captcha Token Applied", "Yes" if self.captcha_token_applied else "No"),
            ("Captcha Accepted", "Yes" if self.captcha_accepted else "No"),
            (
                "Google Blocked After Captcha",
                "Yes" if self.google_blocked_after_captcha else "No",
            ),
            ("Ads Found", self.ads_found),
            ("Num Filtered Ads", self.num_filtered_ads),
            ("Num Excluded Ads", self.num_excluded_ads),
            ("Ads Clicked", self.ads_clicked),
            ("Non-ads Clicked", self.non_ads_clicked),
            ("Shopping Ads Found", self.shopping_ads_found),
            ("Num Filtered Shopping Ads", self.num_filtered_shopping_ads),
            ("Num Excluded Shopping Ads", self.num_excluded_shopping_ads),
            ("Shopping Ads Clicked", self.shopping_ads_clicked),
        ]

        text = "<pre>Summary of Statistics"

        for line in lines:
            if line:
                text += f"\n{line[0]:<25}: {line[1]:<8}"

        text += "</pre>\n"

        return text

    def __str__(self):
        rows = [
            ("Browser ID", self.browser_id) if self.browser_id else None,
            ("Initial Proxy IP", self.initial_proxy_ip) if self.initial_proxy_ip else None,
            ("Latest Proxy IP", self.latest_proxy_ip) if self.latest_proxy_ip else None,
            ("IP Changed Mid-session", "Yes" if self.ip_changed_mid_session else "No"),
            (
                "Proxy Tunnel Failed",
                "Yes" if self.proxy_tunnel_connection_failed else "No",
            ),
            ("Captcha Seen", "Yes" if self.captcha_seen else "No"),
            ("Captcha Token Received", "Yes" if self.captcha_token_received else "No"),
            ("Captcha Token Applied", "Yes" if self.captcha_token_applied else "No"),
            ("Captcha Accepted", "Yes" if self.captcha_accepted else "No"),
            (
                "Google Blocked After Captcha",
                "Yes" if self.google_blocked_after_captcha else "No",
            ),
            ("Ads Found", self.ads_found),
            ("Num Filtered Ads", self.num_filtered_ads),
            ("Num Excluded Ads", self.num_excluded_ads),
            ("Ads Clicked", self.ads_clicked),
            ("Non-ads Clicked", self.non_ads_clicked),
            ("Shopping Ads Found", self.shopping_ads_found),
            ("Num Filtered Shopping Ads", self.num_filtered_shopping_ads),
            ("Num Excluded Shopping Ads", self.num_excluded_shopping_ads),
            ("Shopping Ads Clicked", self.shopping_ads_clicked),
        ]

        border = "+" + "-" * 27 + "+" + "-" * 10 + "+"
        table = ["Summary of Statistics", border]

        for row in rows:
            if row:
                row_str = f"| {row[0]:<25} | {row[1]:<8} |"
                table.append(row_str)

        table.append(border)

        return "\n".join(table)
