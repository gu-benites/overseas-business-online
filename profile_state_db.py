from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

from browser_cleanup import CITY_PROFILE_BASE_DIR, list_active_reserved_paths
from logger import logger


DBCursor = sqlite3.Cursor
DEFAULT_DB_PATH = Path("profile_state.db")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_timestamp(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _slugify_city(city_name: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "-" for character in city_name)
    normalized = "-".join(part for part in normalized.split("-") if part)
    return normalized or "city"


def build_profile_key(city_name: str, key_mode: str = "city") -> str:
    if key_mode != "city":
        raise ValueError(f"Unsupported profile reuse key mode: {key_mode}")
    return _slugify_city(city_name)


@dataclass(slots=True)
class ProfileState:
    profile_key: str
    city_name: str
    rsw_id: Optional[str]
    profile_dir: str
    created_at: str
    last_used_at: str
    expires_at: str
    last_proxy_ip: Optional[str]
    last_proxy_session_id: Optional[str]
    risk_score: int
    last_seeded_at: Optional[str]
    status: str
    recycle_reason: Optional[str]

    @property
    def profile_path(self) -> Path:
        return Path(self.profile_dir)


class ProfileStateDB:
    """SQLite persistence for reusable city-scoped browser profiles."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._create_tables()

    def get_profile(self, profile_key: str) -> Optional[ProfileState]:
        with self._db_cursor() as cursor:
            cursor.execute("SELECT * FROM profile_states WHERE profile_key = ?", (profile_key,))
            row = cursor.fetchone()
        return self._row_to_state(row) if row else None

    def ensure_profile(
        self,
        *,
        profile_key: str,
        city_name: str,
        rsw_id: Optional[str],
        ttl_minutes: int,
    ) -> ProfileState:
        existing = self.get_profile(profile_key)
        now = datetime.now(UTC).replace(microsecond=0)
        expires_at = now + timedelta(minutes=max(1, int(ttl_minutes or 1)))
        profile_dir = CITY_PROFILE_BASE_DIR / profile_key

        if existing:
            with self._db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE profile_states
                    SET city_name = ?, rsw_id = ?, profile_dir = ?, last_used_at = ?, expires_at = ?
                    WHERE profile_key = ?
                    """,
                    (
                        city_name,
                        str(rsw_id) if rsw_id is not None else None,
                        str(profile_dir),
                        now.isoformat(),
                        expires_at.isoformat(),
                        profile_key,
                    ),
                )
            return self.get_profile(profile_key)  # type: ignore[return-value]

        with self._db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO profile_states (
                    profile_key, city_name, rsw_id, profile_dir, created_at, last_used_at, expires_at,
                    last_proxy_ip, last_proxy_session_id, risk_score, last_seeded_at, status, recycle_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0, NULL, 'active', NULL)
                """,
                (
                    profile_key,
                    city_name,
                    str(rsw_id) if rsw_id is not None else None,
                    str(profile_dir),
                    now.isoformat(),
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
        return self.get_profile(profile_key)  # type: ignore[return-value]

    def record_proxy_observation(
        self,
        profile_key: str,
        *,
        proxy_ip: Optional[str],
        proxy_session_id: Optional[str],
        ttl_minutes: int,
    ) -> None:
        now = datetime.now(UTC).replace(microsecond=0)
        expires_at = now + timedelta(minutes=max(1, int(ttl_minutes or 1)))
        with self._db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE profile_states
                SET last_used_at = ?, expires_at = ?, last_proxy_ip = ?, last_proxy_session_id = ?
                WHERE profile_key = ?
                """,
                (
                    now.isoformat(),
                    expires_at.isoformat(),
                    proxy_ip,
                    proxy_session_id,
                    profile_key,
                ),
            )

    def mark_seeded(self, profile_key: str) -> None:
        with self._db_cursor() as cursor:
            cursor.execute(
                "UPDATE profile_states SET last_seeded_at = ? WHERE profile_key = ?",
                (_utc_now(), profile_key),
            )

    def adjust_risk(self, profile_key: str, delta: int, *, reason: Optional[str] = None) -> int:
        current = self.get_profile(profile_key)
        if not current:
            return 0

        next_score = max(0, int(current.risk_score) + int(delta))
        with self._db_cursor() as cursor:
            cursor.execute(
                "UPDATE profile_states SET risk_score = ?, recycle_reason = COALESCE(?, recycle_reason) "
                "WHERE profile_key = ?",
                (next_score, reason, profile_key),
            )
        return next_score

    def mark_recycle(self, profile_key: str, reason: str) -> None:
        with self._db_cursor() as cursor:
            cursor.execute(
                "UPDATE profile_states SET status = 'recycle_pending', recycle_reason = ? "
                "WHERE profile_key = ?",
                (reason, profile_key),
            )

    def reset_profile(self, profile_key: str) -> None:
        with self._db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE profile_states
                SET risk_score = 0, last_seeded_at = NULL, status = 'active', recycle_reason = NULL,
                    last_proxy_ip = NULL, last_proxy_session_id = NULL
                WHERE profile_key = ?
                """,
                (profile_key,),
            )

    def remove_profile_record(self, profile_key: str) -> None:
        with self._db_cursor() as cursor:
            cursor.execute("DELETE FROM profile_states WHERE profile_key = ?", (profile_key,))

    def cleanup_expired_or_recycled_profiles(self) -> list[str]:
        active_reserved_paths = list_active_reserved_paths()
        removed: list[str] = []
        now = datetime.now(UTC).replace(microsecond=0)

        with self._db_cursor() as cursor:
            cursor.execute("SELECT * FROM profile_states")
            rows = cursor.fetchall()

        for row in rows:
            state = self._row_to_state(row)
            if not state:
                continue

            recycle_pending = state.status == "recycle_pending"
            expired = False
            expires_at = _parse_timestamp(state.expires_at)
            if expires_at and expires_at <= now:
                expired = True

            profile_path = state.profile_path
            normalized_path = str(profile_path.resolve(strict=False))
            if normalized_path in active_reserved_paths:
                continue

            if not recycle_pending and not expired and profile_path.exists():
                continue

            try:
                shutil.rmtree(profile_path, ignore_errors=True)
            except Exception as exp:
                logger.debug(f"Failed to cleanup reusable profile dir '{profile_path}': {exp}")
                continue

            self.remove_profile_record(state.profile_key)
            removed.append(state.profile_key)

        if removed:
            logger.info(
                "Reusable profile cleanup removed %d expired/recycled profile(s): %s",
                len(removed),
                ", ".join(sorted(removed)),
            )

        return removed

    def _create_tables(self) -> None:
        with self._db_cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_states (
                    profile_key TEXT PRIMARY KEY NOT NULL,
                    city_name TEXT NOT NULL,
                    rsw_id TEXT,
                    profile_dir TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_proxy_ip TEXT,
                    last_proxy_session_id TEXT,
                    risk_score INTEGER NOT NULL DEFAULT 0,
                    last_seeded_at TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    recycle_reason TEXT
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_profile_states_status ON profile_states(status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_profile_states_expires_at ON profile_states(expires_at)"
            )

    def _row_to_state(self, row: sqlite3.Row | tuple | None) -> Optional[ProfileState]:
        if not row:
            return None
        return ProfileState(
            profile_key=row[0],
            city_name=row[1],
            rsw_id=row[2],
            profile_dir=row[3],
            created_at=row[4],
            last_used_at=row[5],
            expires_at=row[6],
            last_proxy_ip=row[7],
            last_proxy_session_id=row[8],
            risk_score=int(row[9] or 0),
            last_seeded_at=row[10],
            status=row[11],
            recycle_reason=row[12],
        )

    @contextmanager
    def _db_cursor(self) -> Iterator[DBCursor]:
        connection = sqlite3.connect(self.db_path)
        try:
            yield connection.cursor()
        finally:
            connection.commit()
            connection.close()
