from contextlib import contextmanager
from datetime import datetime
from typing import Iterable, Optional

import sqlite3

from logger import logger


DBCursor = sqlite3.Connection.cursor


class SearchImpressionsDB:
    """SQLite database for ad impressions seen in search results."""

    def __init__(self) -> None:
        self._create_db_table()

    def save_impressions(
        self,
        impressions: Iterable[dict[str, object]],
        *,
        search_run_id: str,
        query: str,
        city_name: str | None = None,
        rsw_id: str | None = None,
        grouped_cycle_id: str | None = None,
        impression_timestamp: str | None = None,
    ) -> int:
        rows = list(impressions)
        if not rows:
            return 0

        resolved_timestamp = impression_timestamp or datetime.now().isoformat(timespec="seconds")

        try:
            with self._db() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO search_impressions (
                        impression_date,
                        impression_timestamp,
                        search_run_id,
                        grouped_cycle_id,
                        city_name,
                        rsw_id,
                        query,
                        category,
                        result_position,
                        title,
                        shown_url,
                        click_url,
                        target_domain,
                        eligible_for_click,
                        filter_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            datetime.now().strftime("%d-%m-%Y"),
                            resolved_timestamp,
                            search_run_id,
                            grouped_cycle_id,
                            city_name,
                            rsw_id,
                            query,
                            row.get("category"),
                            row.get("result_position"),
                            row.get("title"),
                            row.get("shown_url"),
                            row.get("click_url"),
                            row.get("target_domain"),
                            1 if row.get("eligible_for_click") else 0,
                            row.get("filter_reason"),
                        )
                        for row in rows
                    ],
                )
            logger.debug(
                "Saved %d search impression(s): run_id=%s, city=%s, query=%s",
                len(rows),
                search_run_id,
                city_name,
                query,
            )
            return len(rows)
        except sqlite3.Error as exp:
            raise RuntimeError(exp) from exp

    def query_impressions_for_cycle(self, grouped_cycle_id: str) -> list[tuple]:
        with self._db() as cursor:
            cursor.execute(
                """
                SELECT
                    impression_timestamp,
                    COALESCE(search_run_id, ''),
                    COALESCE(city_name, ''),
                    COALESCE(rsw_id, ''),
                    query,
                    category,
                    result_position,
                    COALESCE(title, ''),
                    COALESCE(shown_url, ''),
                    COALESCE(click_url, ''),
                    COALESCE(target_domain, ''),
                    eligible_for_click,
                    COALESCE(filter_reason, '')
                FROM search_impressions
                WHERE grouped_cycle_id = ?
                ORDER BY impression_timestamp ASC, category ASC, result_position ASC, id ASC
                """,
                (grouped_cycle_id,),
            )
            return cursor.fetchall()

    def query_impressions_by_date(self, impression_date: str) -> list[tuple]:
        with self._db() as cursor:
            cursor.execute(
                """
                SELECT
                    impression_timestamp,
                    COALESCE(search_run_id, ''),
                    COALESCE(city_name, ''),
                    COALESCE(rsw_id, ''),
                    query,
                    category,
                    result_position,
                    COALESCE(title, ''),
                    COALESCE(shown_url, ''),
                    COALESCE(click_url, ''),
                    COALESCE(target_domain, ''),
                    eligible_for_click,
                    COALESCE(filter_reason, '')
                FROM search_impressions
                WHERE impression_date = ?
                ORDER BY impression_timestamp ASC, category ASC, result_position ASC, id ASC
                """,
                (impression_date,),
            )
            return cursor.fetchall()

    def _create_db_table(self) -> None:
        with self._db() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS search_impressions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    impression_date TEXT NOT NULL,
                    impression_timestamp TEXT NOT NULL,
                    search_run_id TEXT NOT NULL,
                    grouped_cycle_id TEXT,
                    city_name TEXT,
                    rsw_id TEXT,
                    query TEXT NOT NULL,
                    category TEXT NOT NULL,
                    result_position INTEGER,
                    title TEXT,
                    shown_url TEXT,
                    click_url TEXT,
                    target_domain TEXT,
                    eligible_for_click INTEGER NOT NULL DEFAULT 0,
                    filter_reason TEXT
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_search_impressions_cycle_run "
                "ON search_impressions(grouped_cycle_id, search_run_id, category, result_position, id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_search_impressions_run "
                "ON search_impressions(search_run_id, category, result_position, id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_search_impressions_date "
                "ON search_impressions(impression_date, impression_timestamp, id)"
            )

    @contextmanager
    def _db(self) -> DBCursor:
        try:
            db = sqlite3.connect("search_impressions.db")
            yield db.cursor()
        except sqlite3.Error as exp:
            logger.error(exp)
            raise RuntimeError("Failed to connect to search impressions database!") from exp
        finally:
            db.commit()
            db.close()
