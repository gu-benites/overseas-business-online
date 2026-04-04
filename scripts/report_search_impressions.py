import argparse
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from search_impressions_db import SearchImpressionsDB


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print detailed search impression events from search_impressions.db."
    )
    parser.add_argument(
        "--date",
        help="Date in DD-MM-YYYY format. Defaults to today.",
    )
    parser.add_argument(
        "--city",
        help="Optional city_name filter.",
    )
    parser.add_argument(
        "--cycle",
        help="Optional grouped_cycle_id filter.",
    )
    return parser


def _truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def main() -> None:
    args = get_arg_parser().parse_args()
    report_date = args.date or datetime.now().strftime("%d-%m-%Y")
    db = SearchImpressionsDB()

    if args.cycle:
        rows = db.query_impressions_for_cycle(args.cycle)
    else:
        rows = db.query_impressions_by_date(report_date)

    if args.city:
        rows = [row for row in rows if (row[2] or "").lower() == args.city.lower()]

    if not rows:
        scope = args.cycle or report_date
        print(f"No search impressions found for {scope}.")
        return

    headers = (
        "Timestamp",
        "City",
        "RSW",
        "Pos",
        "Category",
        "Eligible",
        "Run ID",
        "Query",
        "Title",
        "Shown URL",
        "Click URL",
        "Reason",
    )
    widths = (19, 16, 6, 4, 10, 8, 30, 28, 28, 44, 44, 18)
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    print(border)
    print(
        "| "
        + " | ".join(f"{header:<{width}}" for header, width in zip(headers, widths))
        + " |"
    )
    print(border)

    for (
        impression_timestamp,
        search_run_id,
        city_name,
        rsw_id,
        query,
        category,
        result_position,
        title,
        shown_url,
        click_url,
        _target_domain,
        eligible_for_click,
        filter_reason,
    ) in rows:
        values = (
            impression_timestamp or "-",
            city_name or "-",
            rsw_id or "-",
            str(result_position) if result_position is not None else "-",
            category or "-",
            "yes" if eligible_for_click else "no",
            search_run_id or "-",
            query or "-",
            title or "-",
            shown_url or "-",
            click_url or "-",
            filter_reason or "-",
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
