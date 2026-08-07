"""SQLite connection helper — applies data/schema.sql on first use."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: Path, schema_path: Path) -> sqlite3.Connection:
    """Opens a SQLite connection, applying the schema on first use.

    Args:
        db_path: Path to the SQLite database file. Its parent directory is
            created if needed.
        schema_path: Path to the SQL script that defines match/set/point.
            Only executed if db_path didn't already exist, so it's safe to
            call this repeatedly against the same database.

    Returns:
        An open connection with foreign key enforcement turned on.
    """
    is_new = not db_path.exists()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    if is_new:
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        connection.commit()
    return connection
