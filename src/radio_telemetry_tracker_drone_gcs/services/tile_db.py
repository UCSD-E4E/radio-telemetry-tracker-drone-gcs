"""tile_db.py: direct SQLite code for tile caching (read/write)."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from queue import Empty, Full, Queue
from threading import Lock
from typing import TYPE_CHECKING

from radio_telemetry_tracker_drone_gcs.utils.paths import ensure_app_dir, get_db_path

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)

ensure_app_dir()  # Ensure app directory exists
DB_PATH = get_db_path()

# Connection pool
MAX_CONNECTIONS = 5
_connection_pool: Queue[sqlite3.Connection] = Queue(maxsize=MAX_CONNECTIONS)
_pool_lock = Lock()


def _create_connection() -> sqlite3.Connection:
    """Create a new optimized database connection."""
    conn = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-2000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _get_connection() -> sqlite3.Connection:
    """Get a connection from the pool or create a new one."""
    try:
        return _connection_pool.get_nowait()
    except Empty:
        return _create_connection()


def _return_connection(conn: sqlite3.Connection) -> None:
    """Return a connection to the pool or close it if pool is full."""
    try:
        _connection_pool.put_nowait(conn)
    except Full:
        conn.close()


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection]:
    """Get a database connection from the pool."""
    conn = None
    try:
        conn = _get_connection()
        # Set optimized connection settings
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-2000")
        yield conn
    except sqlite3.Error:
        logger.exception("Database error")
        raise
    finally:
        if conn:
            _return_connection(conn)


def get_tile_db(z: int, x: int, y: int, source: str) -> bytes | None:
    """Retrieve a tile from DB if cached."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT data FROM tiles WHERE z=? AND x=? AND y=? AND source=?",
                (z, x, y, source),
            )
            row = cursor.fetchone()
            return row[0] if row else None
    except sqlite3.Error:
        logger.exception("Error retrieving tile")
        return None


def store_tile_db(z: int, x: int, y: int, source: str, data: bytes) -> bool:
    """Store or update tile in DB. Returns success status."""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tiles (z, x, y, source, data) VALUES (?, ?, ?, ?, ?)",
                (z, x, y, source, data),
            )
            conn.commit()
            return True
    except sqlite3.Error:
        logger.exception("Error storing tile")
        return False


def clear_tile_cache_db() -> int:
    """Delete all cached tiles. Return number of rows removed."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM tiles")
            conn.commit()
            return cursor.rowcount
    except sqlite3.Error:
        logger.exception("Error clearing tile cache")
        return 0


def get_tile_info_db() -> dict:
    """Return tile count and size in MB."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(data)), 0) FROM tiles")
            count, size = cursor.fetchone() or (0, 0)
            return {
                "total_tiles": count,
                "total_size_mb": round(size / (1024 * 1024), 2),
            }
    except sqlite3.Error:
        logger.exception("Error getting tile info")
        return {"total_tiles": 0, "total_size_mb": 0.0}


def init_db() -> None:
    """Initialize the tile DB (and POI table) if not exists."""
    try:
        with get_db_connection() as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")

            # Create tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tiles (
                    z INTEGER,
                    x INTEGER,
                    y INTEGER,
                    source TEXT,
                    data BLOB,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (z, x, y, source)
                )
            """)

            # Add index on timestamp for cleanup operations
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tiles_timestamp ON tiles(timestamp)")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS pois (
                    name TEXT PRIMARY KEY,
                    latitude REAL,
                    longitude REAL
                )
            """)

            # Add spatial index on POI coordinates
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pois_coords ON pois(latitude, longitude)")

            # Add periodic cleanup trigger
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS cleanup_old_tiles
                AFTER INSERT ON tiles
                BEGIN
                    DELETE FROM tiles
                    WHERE timestamp < datetime('now', '-30 days')
                    AND rowid NOT IN (
                        SELECT rowid FROM tiles
                        ORDER BY timestamp DESC
                        LIMIT 10000
                    );
                END;
            """)

            conn.commit()
    except sqlite3.Error:
        logger.exception("Error initializing database")
        raise
