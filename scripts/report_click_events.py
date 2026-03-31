import argparse
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clicklogs_db import ClickLogsDB


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print detailed click events from clicklogs.db."
    )
    parser.add_argument(
        "--date",
        help="Date in DD-MM-YYYY format. Defaults to today.",
    )
    parser.add_argument(
        "--city",
        help="Optional city_name filter.",
    )
    return parser


def _truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def main() -> None:
    args = get_arg_parser().parse_args()
    report_date = args.date or datetime.now().strftime("%d-%m-%Y")
    rows = ClickLogsDB().query_click_events_by_date(report_date)

    if args.city:
        rows = [row for row in rows if (row[2] or "").lower() == args.city.lower()]

    if not rows:
        print(f"No click events found for {report_date}.")
        return

    headers = (
        "Timestamp",
        "City",
        "RSW",
        "Pos",
        "Category",
        "Click ID",
        "Run ID",
        "Query",
        "Result URL",
        "Final URL",
    )
    widths = (19, 16, 6, 4, 10, 32, 30, 32, 56, 56)
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    print(border)
    print(
        "| "
        + " | ".join(f"{header:<{width}}" for header, width in zip(headers, widths))
        + " |"
    )
    print(border)

    for (
        click_id,
        search_run_id,
        city_name,
        rsw_id,
        click_timestamp,
        query,
        category,
        _site_url,
        result_url,
        final_url,
        result_position,
    ) in rows:
        values = (
            click_timestamp or "-",
            city_name or "-",
            rsw_id or "-",
            str(result_position) if result_position is not None else "-",
            category or "-",
            click_id or "-",
            search_run_id or "-",
            query or "-",
            result_url or "-",
            final_url or "-",
        )
        print(
            "| "
            + " | ".join(
                f"{_truncate(value, width):<{width}}"
                for value, width in zip(values, widths)
            )
            + " |"
        )

    print(border)


if __name__ == "__main__":
    main()
