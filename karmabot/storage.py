# Copyright (c) 2019 Target Brands, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import os
import sqlite3
from pathlib import Path


KARMA_TYPES = ("thing", "user", "channel", "group")


def _to_db_datetime(value):
    return value.replace(microsecond=0).isoformat()


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class KarmaStore(object):
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS karma_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    gifter TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_karma_subject
                    ON karma_events (workspace_id, subject_type, subject);
                CREATE INDEX IF NOT EXISTS idx_karma_gifter_created
                    ON karma_events (workspace_id, gifter, created_at);
                CREATE INDEX IF NOT EXISTS idx_karma_expires
                    ON karma_events (workspace_id, expires_at);
                """
            )

    def cleanup_expired(self, workspace_id):
        now = _to_db_datetime(_utcnow())
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM karma_events WHERE workspace_id = ? AND expires_at <= ?",
                (workspace_id, now),
            )

    def count_recent_gifts(self, workspace_id, gifter, since):
        self.cleanup_expired(workspace_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM karma_events
                WHERE workspace_id = ? AND gifter = ? AND created_at > ?
                """,
                (workspace_id, gifter, _to_db_datetime(since)),
            ).fetchone()
            return row["total"]

    def store_karma(self, workspace_id, subject_type, subject, quantity, gifter, created_at, expires_at):
        self.cleanup_expired(workspace_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO karma_events (
                    workspace_id, subject_type, subject, quantity, gifter, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace_id,
                    subject_type,
                    subject,
                    quantity,
                    gifter,
                    _to_db_datetime(created_at),
                    _to_db_datetime(expires_at),
                ),
            )

    def get_karma(self, workspace_id, subject_type, subject):
        self.cleanup_expired(workspace_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(quantity), 0) AS total
                FROM karma_events
                WHERE workspace_id = ? AND subject_type = ? AND subject = ?
                """,
                (workspace_id, subject_type, subject),
            ).fetchone()
            return row["total"]

    def get_type_karma(self, workspace_id, subject_type):
        self.cleanup_expired(workspace_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(quantity), 0) AS total
                FROM karma_events
                WHERE workspace_id = ? AND subject_type = ?
                """,
                (workspace_id, subject_type),
            ).fetchone()
            return row["total"]

    def get_all_karma(self, workspace_id):
        self.cleanup_expired(workspace_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) AS total FROM karma_events WHERE workspace_id = ?",
                (workspace_id,),
            ).fetchone()
            return row["total"]

    def get_karma_gifter_count(self, workspace_id):
        self.cleanup_expired(workspace_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(DISTINCT gifter) AS total FROM karma_events WHERE workspace_id = ?",
                (workspace_id,),
            ).fetchone()
            return row["total"]

    def get_subject_count(self, workspace_id, subject_type=None):
        self.cleanup_expired(workspace_id)
        args = [workspace_id]
        where = "workspace_id = ?"
        if subject_type:
            where = f"{where} AND subject_type = ?"
            args.append(subject_type)

        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM (
                    SELECT subject_type, subject
                    FROM karma_events
                    WHERE {where}
                    GROUP BY subject_type, subject
                )
                """,
                args,
            ).fetchone()
            return row["total"]

    def count_karma_operations(self, workspace_id, subject_type=None, subject=None):
        self.cleanup_expired(workspace_id)
        args = [workspace_id]
        where = "workspace_id = ?"
        if subject_type:
            where = f"{where} AND subject_type = ?"
            args.append(subject_type)
        else:
            placeholders = ", ".join("?" for _ in KARMA_TYPES)
            where = f"{where} AND subject_type IN ({placeholders})"
            args.extend(KARMA_TYPES)
        if subject:
            where = f"{where} AND subject = ?"
            args.append(subject)

        with self._connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS total FROM karma_events WHERE {where}",
                args,
            ).fetchone()
            return row["total"]

    def get_top_karma(self, workspace_id, gifter=None, subject_type=None, direction=-1, limit=10, subjects=None):
        self.cleanup_expired(workspace_id)
        args = [workspace_id]
        where = "workspace_id = ?"
        if gifter:
            where = f"{where} AND gifter = ?"
            args.append(gifter)
        if subject_type:
            where = f"{where} AND subject_type = ?"
            args.append(subject_type)
        else:
            placeholders = ", ".join("?" for _ in KARMA_TYPES)
            where = f"{where} AND subject_type IN ({placeholders})"
            args.extend(KARMA_TYPES)
        if subjects is not None:
            if not subjects:
                return []
            placeholders = ", ".join("?" for _ in subjects)
            where = f"{where} AND subject IN ({placeholders})"
            args.extend(subjects)

        direction_sql = "ASC" if direction == 1 else "DESC"
        args.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT subject_type, subject, SUM(quantity) AS total
                FROM karma_events
                WHERE {where}
                GROUP BY subject_type, subject
                ORDER BY total {direction_sql}
                LIMIT ?
                """,
                args,
            ).fetchall()
            return [dict(row) for row in rows]

    def get_gifters(self, workspace_id, subject_type, subject):
        self.cleanup_expired(workspace_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT gifter, SUM(quantity) AS total
                FROM karma_events
                WHERE workspace_id = ? AND subject_type = ? AND subject = ?
                GROUP BY gifter
                ORDER BY total DESC
                """,
                (workspace_id, subject_type, subject),
            ).fetchall()
            return [(row["gifter"], row["total"]) for row in rows]

_store = None


def get_store(path):
    global _store
    expanded_path = os.path.abspath(os.path.expanduser(path))
    if _store is None or str(_store.path) != expanded_path:
        _store = KarmaStore(expanded_path)
    return _store
