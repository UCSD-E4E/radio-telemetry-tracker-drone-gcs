"""SQLite database operations for managing points of interest (POIs)."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from typing import TYPE_CHECKING

from radio_telemetry_tracker_drone_gcs.utils.paths import get_db_path

if TYPE_CHECKING:
    from collections.abc import Generator

DB_PATH = get_db_path()

# Coordinate boundaries
MIN_LATITUDE = -90
MAX_LATITUDE = 90
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection with optimized settings."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        # Optimize connection
        conn.execute("PRAGMA synchronous=NORMAL")  # Faster than FULL, still safe
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA cache_size=-2000")  # Use 2MB of cache
        yield conn
    except sqlite3.Error:
        logging.exception("Database error")
        raise
    finally:
        if conn:
            conn.close()


def init_db() -> None:
    """Initialize the POI database with optimized settings."""
    try:
        with get_db_connection() as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")

            # Drop existing table if it exists
            conn.execute("DROP TABLE IF EXISTS pois")

            # Create table with correct schema
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pois (
                    name TEXT PRIMARY KEY,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add spatial index on coordinates
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pois_coords ON pois(latitude, longitude)")

            # Add trigger to update timestamp
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_poi_timestamp
                AFTER UPDATE ON pois
                BEGIN
                    UPDATE pois SET updated_at = CURRENT_TIMESTAMP
                    WHERE name = NEW.name;
                END;
            """)

            conn.commit()
    except sqlite3.Error:
        logging.exception("Error initializing POI database")
        raise


def list_pois_db() -> list[dict]:
    """Retrieve all points of interest ordered by name."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT name, latitude, longitude FROM pois ORDER BY name")
            return [{"name": name, "coords": [lat, lng]} for name, lat, lng in cursor]
    except sqlite3.Error:
        logging.exception("Error listing POIs")
        return []


def add_poi_db(name: str, lat: float, lng: float) -> bool:
    """Add or update a POI with validation."""
    if not (MIN_LATITUDE <= lat <= MAX_LATITUDE) or not (MIN_LONGITUDE <= lng <= MAX_LONGITUDE):
        logging.error("Invalid coordinates: lat=%f, lng=%f", lat, lng)
        return False

    try:
        with get_db_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO pois (name, latitude, longitude) VALUES (?, ?, ?)", (name, lat, lng))
            conn.commit()
            return True
    except sqlite3.Error:
        logging.exception("Error adding POI")
        return False


def remove_poi_db(name: str) -> bool:
    """Remove a POI and return success status."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM pois WHERE name = ?", (name,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error:
        logging.exception("Error removing POI")
        return False


def rename_poi_db(old: str, new: str) -> bool:
    """Rename a POI with validation and return success status."""
    if not old or not new:
        return False

    try:
        with get_db_connection() as conn:
            # Check if new name already exists
            cursor = conn.execute("SELECT 1 FROM pois WHERE name = ?", (new,))
            if cursor.fetchone() and old.lower() != new.lower():
                logging.error("POI with name '%s' already exists", new)
                return False

            cursor = conn.execute("UPDATE pois SET name = ? WHERE name = ?", (new, old))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error:
        logging.exception("Error renaming POI")
        return False
