from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Iterator, Optional

from logger import logger


DBCursor = sqlite3.Cursor
DEFAULT_DB_PATH = Path("groups.db")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class GroupRecord:
    id: int
    city_name: str
    rsw_id: str
    proxy: str
    enabled: bool
    last_query_position: int
    created_at: str
    updated_at: str


@dataclass(slots=True)
class GroupQueryRecord:
    id: int
    group_id: int
    query_text: str
    position: int
    created_at: str
    updated_at: str


@dataclass(slots=True)
class GroupRunRecord:
    id: int
    group_id: int
    city_name: str
    rsw_id: str
    started_at: str
    finished_at: Optional[str]
    status: str
    query_used: Optional[str]
    captcha_seen: Optional[bool]
    ads_found: Optional[int]
    ads_clicked: Optional[int]
    notes: Optional[str]


class GroupsDB:
    """SQLite persistence layer for city/proxy/query groups."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._create_tables()

    def create_group(self, city_name: str, rsw_id: str, proxy: str, enabled: bool = True) -> int:
        now = _utc_now()
        with self._db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO groups (city_name, rsw_id, proxy, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (city_name.strip(), rsw_id.strip(), proxy.strip(), int(enabled), now, now),
            )
            group_id = int(cursor.lastrowid)
        logger.info(f"Group created: city={city_name}, rsw_id={rsw_id}, group_id={group_id}")
        return group_id

    def update_group(
        self,
        group_id: int,
        *,
        city_name: Optional[str] = None,
        rsw_id: Optional[str] = None,
        proxy: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        updates: list[str] = []
        params: list[object] = []

        if city_name is not None:
            updates.append("city_name = ?")
            params.append(city_name.strip())
        if rsw_id is not None:
            updates.append("rsw_id = ?")
            params.append(rsw_id.strip())
        if proxy is not None:
            updates.append("proxy = ?")
            params.append(proxy.strip())
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(int(enabled))

        if not updates:
            return

        updates.append("updated_at = ?")
        params.append(_utc_now())
        params.append(group_id)

        with self._db_cursor() as cursor:
            cursor.execute(
                f"UPDATE groups SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            if cursor.rowcount == 0:
                raise RuntimeError(f"Group not found: {group_id}")

    def get_group(self, group_id: int) -> Optional[GroupRecord]:
        with self._db_cursor() as cursor:
            cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
            row = cursor.fetchone()
        return self._row_to_group(row) if row else None

    def list_groups(self, enabled_only: bool = False) -> list[GroupRecord]:
        query = "SELECT * FROM groups"
        params: tuple[object, ...] = ()
        if enabled_only:
            query += " WHERE enabled = ?"
            params = (1,)
        query += " ORDER BY city_name COLLATE NOCASE ASC"
        with self._db_cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [self._row_to_group(row) for row in rows]

    def get_next_query_for_group(self, group_id: int) -> Optional[GroupQueryRecord]:
        selected_query = self.peek_next_query_for_group(group_id)
        if not selected_query:
            return None

        with self._db_cursor() as cursor:
            cursor.execute(
                "UPDATE groups SET last_query_position = ?, updated_at = ? WHERE id = ?",
                (selected_query.position, _utc_now(), group_id),
            )

        return selected_query

    def peek_next_query_for_group(self, group_id: int) -> Optional[GroupQueryRecord]:
        queries = self.get_group_queries(group_id)
        if not queries:
            return None

        group = self.get_group(group_id)
        if not group:
            raise RuntimeError(f"Group not found: {group_id}")

        last_position = max(0, int(group.last_query_position or 0))
        next_index = last_position % len(queries)
        return queries[next_index]

    def replace_group_queries(self, group_id: int, queries: list[str]) -> None:
        cleaned_queries = [query.strip() for query in queries if query and query.strip()]
        now = _utc_now()

        with self._db_cursor() as cursor:
            cursor.execute("SELECT id FROM groups WHERE id = ?", (group_id,))
            if not cursor.fetchone():
                raise RuntimeError(f"Group not found: {group_id}")

            cursor.execute("DELETE FROM group_queries WHERE group_id = ?", (group_id,))
            for position, query_text in enumerate(cleaned_queries, start=1):
                cursor.execute(
                    """
                    INSERT INTO group_queries (group_id, query_text, position, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (group_id, query_text, position, now, now),
                )
            cursor.execute("UPDATE groups SET updated_at = ? WHERE id = ?", (now, group_id))

        logger.info(
            f"Group queries replaced: group_id={group_id}, query_count={len(cleaned_queries)}"
        )

    def get_group_queries(self, group_id: int) -> list[GroupQueryRecord]:
        with self._db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM group_queries WHERE group_id = ? ORDER BY position ASC, id ASC",
                (group_id,),
            )
            rows = cursor.fetchall()
        return [self._row_to_group_query(row) for row in rows]

    def create_run(
        self,
        group_id: int,
        *,
        status: str = "started",
        query_used: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        group = self.get_group(group_id)
        if not group:
            raise RuntimeError(f"Group not found: {group_id}")

        started_at = _utc_now()
        with self._db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO group_runs (
                    group_id, city_name, rsw_id, started_at, finished_at, status,
                    query_used, captcha_seen, ads_found, ads_clicked, notes
                )
                VALUES (?, ?, ?, ?, NULL, ?, ?, NULL, NULL, NULL, ?)
                """,
                (
                    group.id,
                    group.city_name,
                    group.rsw_id,
                    started_at,
                    status,
                    query_used,
                    notes,
                ),
            )
            run_id = int(cursor.lastrowid)
        return run_id

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        query_used: Optional[str] = None,
        captcha_seen: Optional[bool] = None,
        ads_found: Optional[int] = None,
        ads_clicked: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> None:
        finished_at = _utc_now()
        with self._db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE group_runs
                SET finished_at = ?,
                    status = ?,
                    query_used = COALESCE(?, query_used),
                    captcha_seen = ?,
                    ads_found = ?,
                    ads_clicked = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    finished_at,
                    status,
                    query_used,
                    None if captcha_seen is None else int(captcha_seen),
                    ads_found,
                    ads_clicked,
                    notes,
                    run_id,
                ),
            )
            if cursor.rowcount == 0:
                raise RuntimeError(f"Run not found: {run_id}")

    def list_group_runs(self, group_id: Optional[int] = None, limit: int = 50) -> list[GroupRunRecord]:
        query = "SELECT * FROM group_runs"
        params: list[object] = []
        if group_id is not None:
            query += " WHERE group_id = ?"
            params.append(group_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._db_cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [self._row_to_group_run(row) for row in rows]

    def _create_tables(self) -> None:
        with self._db_cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    city_name TEXT NOT NULL UNIQUE,
                    rsw_id TEXT NOT NULL,
                    proxy TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_query_position INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS group_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    group_id INTEGER NOT NULL,
                    query_text TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS group_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    group_id INTEGER NOT NULL,
                    city_name TEXT NOT NULL,
                    rsw_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    query_used TEXT,
                    captcha_seen INTEGER,
                    ads_found INTEGER,
                    ads_clicked INTEGER,
                    notes TEXT,
                    FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_group_queries_group_position "
                "ON group_queries(group_id, position)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_group_runs_group_started "
                "ON group_runs(group_id, started_at DESC)"
            )
            self._ensure_groups_schema(cursor)

    @staticmethod
    def _ensure_groups_schema(cursor: DBCursor) -> None:
        cursor.execute("PRAGMA table_info(groups)")
        group_columns = {row[1] for row in cursor.fetchall()}
        if "last_query_position" not in group_columns:
            cursor.execute(
                "ALTER TABLE groups ADD COLUMN last_query_position INTEGER NOT NULL DEFAULT 0"
            )

    @contextmanager
    def _db_cursor(self) -> Iterator[DBCursor]:
        db = None
        try:
            db = sqlite3.connect(self.db_path)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            yield db.cursor()
        except sqlite3.Error as exp:
            logger.error(exp)
            raise RuntimeError(f"Failed to connect to groups database: {self.db_path}") from exp
        finally:
            if db is not None:
                db.commit()
                db.close()

    @staticmethod
    def _row_to_group(row: sqlite3.Row) -> GroupRecord:
        return GroupRecord(
            id=int(row["id"]),
            city_name=str(row["city_name"]),
            rsw_id=str(row["rsw_id"]),
            proxy=str(row["proxy"]),
            enabled=bool(row["enabled"]),
            last_query_position=int(row["last_query_position"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _row_to_group_query(row: sqlite3.Row) -> GroupQueryRecord:
        return GroupQueryRecord(
            id=int(row["id"]),
            group_id=int(row["group_id"]),
            query_text=str(row["query_text"]),
            position=int(row["position"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _row_to_group_run(row: sqlite3.Row) -> GroupRunRecord:
        captcha_seen = row["captcha_seen"]
        return GroupRunRecord(
            id=int(row["id"]),
            group_id=int(row["group_id"]),
            city_name=str(row["city_name"]),
            rsw_id=str(row["rsw_id"]),
            started_at=str(row["started_at"]),
            finished_at=row["finished_at"],
            status=str(row["status"]),
            query_used=row["query_used"],
            captcha_seen=None if captcha_seen is None else bool(captcha_seen),
            ads_found=row["ads_found"],
            ads_clicked=row["ads_clicked"],
            notes=row["notes"],
        )
