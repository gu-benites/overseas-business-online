from datetime import datetime
from typing import Optional
from contextlib import contextmanager

import sqlite3

from logger import logger


DBCursor = sqlite3.Connection.cursor


class ClickLogsDB:
    """SQLite database to keep daily click logs for links

    Raises RuntimeError if database connection is not established.
    """

    def __init__(self) -> None:
        self._create_db_table()

    def save_click(
        self,
        site_url: str,
        category: str,
        query: str,
        click_time: str,
        city_name: str | None = None,
        rsw_id: str | None = None,
        final_url: str | None = None,
        click_timestamp: str | None = None,
        grouped_cycle_id: str | None = None,
        click_id: str | None = None,
        search_run_id: str | None = None,
        result_position: int | None = None,
        result_url: str | None = None,
    ) -> None:
        """Save click_date, site_url, click_time, query, and category to database

        Raises RuntimeError if an error occurs during the save operation.

        :type site_url: str
        :param site_url: Link clicked
        :type category: str
        :param category: Link category as Ad, Non-ad, or Shopping
        :type query: str
        :param query: Search query used
        :type click_time: str
        :param click_time: Time of the click in hh:mm:ss format
        """

        # replace spaces with %20 in urls
        site_url = site_url.replace(" ", "%20")

        try:
            with self._clicklogs_db() as clicklogs_db_cursor:
                # date will be in DD-MM-YYYY format.
                click_date = datetime.now().strftime("%d-%m-%Y")
                resolved_timestamp = click_timestamp or datetime.now().isoformat(timespec="seconds")

                clicklogs_db_cursor.execute(
                    """
                    INSERT INTO clicklogs (
                        click_date, click_time, site_url, query, category,
                        city_name, rsw_id, final_url, click_timestamp, grouped_cycle_id,
                        click_id, search_run_id, result_position, result_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        click_date,
                        click_time,
                        site_url,
                        query,
                        category,
                        city_name,
                        rsw_id,
                        final_url,
                        resolved_timestamp,
                        grouped_cycle_id,
                        click_id,
                        search_run_id,
                        result_position,
                        result_url,
                    ),
                )
                log_details = (
                    f"{click_date} {click_time}, {site_url}, {query}, {category}, "
                    f"city={city_name}, rsw_id={rsw_id}, final_url={final_url}, cycle={grouped_cycle_id}, "
                    f"click_id={click_id}, run_id={search_run_id}, position={result_position}, "
                    f"result_url={result_url}"
                )
                logger.debug(f"Click log ({log_details}) was added to database.")

        except sqlite3.Error as exp:
            raise RuntimeError(exp) from exp

    def query_clicks(self, click_date: str) -> Optional[list[tuple[str, str, str]]]:
        """Query given date in database and return results grouped by the site_url

        :type click_date: str
        :param click_date: Date to query clicks
        :rtype: list
        :returns: List of (site_url, clicks, category, click_time, query) tuples for the given date
        """

        logger.debug(f"Querying click results for {click_date}...")

        try:
            with self._clicklogs_db() as clicklogs_db_cursor:
                query = """
                    SELECT site_url, COUNT(*) as clicks, category, click_time, query
                    FROM clicklogs
                    WHERE click_date = ?
                    GROUP BY site_url, query, category;
                """
                clicklogs_db_cursor.execute(query, (click_date,))

                results = clicklogs_db_cursor.fetchall()

                if not results:
                    logger.debug(f"Couldn't found any click data for {click_date} in database!")
                    return None
                else:
                    return results

        except sqlite3.Error as exp:
            raise RuntimeError(exp) from exp

    def _create_db_table(self) -> None:
        """Create table to store click_date, click_time, site_url, query, and category"""

        with self._clicklogs_db() as clicklogs_db_cursor:
            clicklogs_db_cursor.execute(
                """CREATE TABLE IF NOT EXISTS clicklogs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    click_date TEXT NOT NULL,
                    click_time TEXT NOT NULL,
                    site_url TEXT NOT NULL,
                    query TEXT NOT NULL,
                    category TEXT NOT NULL,
                    city_name TEXT,
                    rsw_id TEXT,
                    final_url TEXT,
                    click_timestamp TEXT,
                    grouped_cycle_id TEXT,
                    click_id TEXT,
                    search_run_id TEXT,
                    result_position INTEGER,
                    result_url TEXT
                );"""
            )
            existing_columns = {
                row[1]
                for row in clicklogs_db_cursor.execute("PRAGMA table_info(clicklogs)").fetchall()
            }
            for column_name, column_sql in (
                ("city_name", "ALTER TABLE clicklogs ADD COLUMN city_name TEXT"),
                ("rsw_id", "ALTER TABLE clicklogs ADD COLUMN rsw_id TEXT"),
                ("final_url", "ALTER TABLE clicklogs ADD COLUMN final_url TEXT"),
                ("click_timestamp", "ALTER TABLE clicklogs ADD COLUMN click_timestamp TEXT"),
                ("grouped_cycle_id", "ALTER TABLE clicklogs ADD COLUMN grouped_cycle_id TEXT"),
                ("click_id", "ALTER TABLE clicklogs ADD COLUMN click_id TEXT"),
                ("search_run_id", "ALTER TABLE clicklogs ADD COLUMN search_run_id TEXT"),
                ("result_position", "ALTER TABLE clicklogs ADD COLUMN result_position INTEGER"),
                ("result_url", "ALTER TABLE clicklogs ADD COLUMN result_url TEXT"),
            ):
                if column_name not in existing_columns:
                    clicklogs_db_cursor.execute(column_sql)
            clicklogs_db_cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_clicklogs_cycle_timestamp "
                "ON clicklogs(grouped_cycle_id, click_timestamp, id)"
            )
            clicklogs_db_cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_clicklogs_run_id ON clicklogs(search_run_id)"
            )
            clicklogs_db_cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_clicklogs_click_id ON clicklogs(click_id)"
            )

    def query_clicks_for_cycle(
        self, grouped_cycle_id: str
    ) -> list[tuple[str, str, str, str, str, str, str, str, str, int | None]]:
        with self._clicklogs_db() as clicklogs_db_cursor:
            clicklogs_db_cursor.execute(
                """
                SELECT
                    COALESCE(click_id, ''),
                    COALESCE(search_run_id, ''),
                    COALESCE(city_name, ''),
                    COALESCE(rsw_id, ''),
                    COALESCE(final_url, site_url),
                    COALESCE(click_timestamp, click_date || 'T' || click_time),
                    query,
                    category,
                    COALESCE(result_url, site_url),
                    result_position
                FROM clicklogs
                WHERE grouped_cycle_id = ?
                ORDER BY click_timestamp ASC, id ASC
                """,
                (grouped_cycle_id,),
            )
            return clicklogs_db_cursor.fetchall()

    def query_click_events_by_date(
        self, click_date: str
    ) -> list[tuple[str, str, str, str, str, str, str, str, str, str, int | None]]:
        with self._clicklogs_db() as clicklogs_db_cursor:
            clicklogs_db_cursor.execute(
                """
                SELECT
                    COALESCE(click_id, ''),
                    COALESCE(search_run_id, ''),
                    COALESCE(city_name, ''),
                    COALESCE(rsw_id, ''),
                    COALESCE(click_timestamp, click_date || 'T' || click_time),
                    query,
                    category,
                    COALESCE(site_url, ''),
                    COALESCE(result_url, site_url, ''),
                    COALESCE(final_url, site_url, ''),
                    result_position
                FROM clicklogs
                WHERE click_date = ?
                ORDER BY click_timestamp ASC, id ASC
                """,
                (click_date,),
            )
            return clicklogs_db_cursor.fetchall()

    @contextmanager
    def _clicklogs_db(self) -> DBCursor:
        """Context manager that returns clicklogs db cursor

        :rtype: sqlite3.Connection.cursor
        :returns: Database connection cursor
        """

        try:
            clicklogs_db = sqlite3.connect("clicklogs.db")
            yield clicklogs_db.cursor()

        except sqlite3.Error as exp:
            logger.error(exp)
            raise RuntimeError("Failed to connect to clicklogs database!") from exp

        finally:
            clicklogs_db.commit()
            clicklogs_db.close()
