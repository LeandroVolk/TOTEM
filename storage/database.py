"""SQLite com migracoes pequenas e conexoes curtas por operacao."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 1


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def migrate(self):
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
            )
            atual = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
            if atual is None:
                atual = 0
            if atual < 1:
                self._migracao_1(connection)
                connection.execute("INSERT INTO schema_migrations(version) VALUES (1)")
            if atual > SCHEMA_VERSION:
                raise RuntimeError("Banco criado por uma versao mais nova do Totem.")

    @staticmethod
    def _migracao_1(connection):
        connection.executescript(
            """
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL CHECK(status IN ('started', 'completed', 'abandoned')),
                content_bundle_id TEXT NOT NULL,
                content_bundle_version TEXT NOT NULL,
                content_bundle_hash TEXT NOT NULL,
                theme_id TEXT,
                questions_answered INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream TEXT NOT NULL CHECK(stream IN ('runtime', 'admin')),
                session_id TEXT REFERENCES sessions(session_id),
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX events_timestamp_idx ON events(timestamp);
            CREATE INDEX events_type_idx ON events(event_type);
            CREATE INDEX events_session_idx ON events(session_id);

            CREATE TABLE content_publications (
                publication_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bundle_id TEXT NOT NULL,
                bundle_version TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('published', 'active', 'superseded')),
                created_at TEXT NOT NULL,
                activated_at TEXT,
                UNIQUE(bundle_id, bundle_version)
            );
            """
        )
