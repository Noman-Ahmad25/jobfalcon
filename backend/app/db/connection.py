from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from app.core.config import get_settings


def resolve_sqlite_path(database_url: str) -> str:
    """Extracts filesystem path from SQLite database URL."""
    if database_url == "sqlite:///:memory:":
        return ":memory:"
    if database_url.startswith("sqlite:///"):
        path_str = database_url[len("sqlite:///") :]
        # Handle relative or absolute paths
        if path_str.startswith("./"):
            # Resolve deterministically relative to backend root directory
            backend_dir = Path(__file__).resolve().parents[2]
            return str((backend_dir / path_str[2:]).resolve())
        return path_str
    return database_url


class DatabaseManager:
    """Manages relational database connections, pragmas, and schema initialization."""

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or get_settings().DATABASE_URL
        self._is_sqlite = self.database_url.startswith("sqlite")
        self._sqlite_path = resolve_sqlite_path(self.database_url) if self._is_sqlite else None
        self._initialized = False

    def get_raw_connection(self) -> sqlite3.Connection:
        """Creates a configured sqlite3 connection with WAL mode and foreign keys enabled."""
        if not self._is_sqlite:
            raise NotImplementedError(
                f"Direct driver for '{self.database_url}' is not configured in this milestone."
            )

        if self._sqlite_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self._sqlite_path)), exist_ok=True)

        conn = sqlite3.connect(
            self._sqlite_path,
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None,  # Explicit transaction control
        )
        conn.row_factory = sqlite3.Row

        # Enforce foreign key constraints and optimal journaling
        conn.execute("PRAGMA foreign_keys = ON;")
        if self._sqlite_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")

        return conn

    def initialize_schema(self) -> None:
        """Applies initial schema migrations if tables do not exist."""
        if not self._is_sqlite:
            return

        migration_file = Path(__file__).parent / "migrations" / "001_initial_schema_sqlite.sql"
        if not migration_file.exists():
            raise FileNotFoundError(f"Migration script not found at {migration_file}")

        with open(migration_file, "r", encoding="utf-8") as f:
            ddl_script = f.read()

        conn = self.get_raw_connection()
        try:
            conn.executescript(ddl_script)
            self._initialized = True
        finally:
            conn.close()

    @contextmanager
    def read_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing a read connection without acquiring exclusive write locks."""
        if not self._initialized and self._is_sqlite:
            self.initialize_schema()

        conn = self.get_raw_connection()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an ACID transactional boundary."""
        if not self._initialized and self._is_sqlite:
            self.initialize_schema()

        conn = self.get_raw_connection()
        in_tx = False
        try:
            conn.execute("BEGIN IMMEDIATE;")
            in_tx = True
            yield conn
            conn.execute("COMMIT;")
            in_tx = False
        except Exception:
            if in_tx:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
            raise
        finally:
            conn.close()


# Default singleton instance
db_manager = DatabaseManager()
