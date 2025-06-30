"""Database utilities for managing tracking sessions and frequency data."""

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from radio_telemetry_tracker_drone_gcs.utils.paths import get_db_path

logger = logging.getLogger(__name__)

DB_PATH = get_db_path()

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection]:
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
        logger.exception("Database error")
        raise
    finally:
        if conn:
            conn.close()

def init_db() -> None:
    """Initialize the database with tables for tracking sessions and frequency data."""
    try:
        with get_db_connection() as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")

            # Drop existing tables if they exist
            conn.execute("DROP TABLE IF EXISTS tracking_sessions")
            conn.execute("DROP TABLE IF EXISTS frequency_data")

            # Create tracking_sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracking_sessions (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    date TIMESTAMP NOT NULL
                )
            """)

            # Create frequency_data table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS frequency_data (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER,
                    frequency INTEGER NOT NULL,
                    data_type TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    amplitude REAL,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES tracking_sessions(id)
                )
            """)

            conn.commit()
    except sqlite3.Error:
        logger.exception("Error initializing database")
        raise

def add_tracking_session(name: str, date: str) -> int:
    """Add a new tracking session to the database and return the session's ID."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO tracking_sessions (name, date)
                VALUES (?, ?)
            """, (name, date))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error:
        logger.exception("Error adding tracking session")
        return -1

def add_frequency(# noqa: PLR0913
    frequency: int,
    data_type: str,
    latitude: float,
    longitude: float,
    amplitude: float,
    session_id: int,
    timestamp: int,
) -> bool:
    """Add a frequency record to the database associated with the given session ID."""
    try:
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO frequency_data (session_id, frequency, data_type, latitude, longitude, amplitude, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, frequency, data_type, latitude, longitude, amplitude, timestamp))
            conn.commit()
            return True
    except sqlite3.Error:
        logger.exception("Error adding frequency data")
        return False

def save_frequencies_to_session(session_name: str, session_date: str, frequencies: list[dict]) -> int:
    """Create a new tracking session and save the frequencies associated with it."""
    session_id = add_tracking_session(session_name, session_date)
    if session_id == -1:
        return -1

    for freq in frequencies:
        success = add_frequency(
            frequency=freq["frequency"],
            data_type=freq["data_type"],
            latitude=freq["latitude"],
            longitude=freq["longitude"],
            amplitude=freq["amplitude"],
            session_id=session_id,
            timestamp=freq["timestamp"],
        )
        if not success:
            logger.error("Failed to add frequency data for session %s", session_name)
            return -1

    return session_id

def get_session_id_by_name(session_name: str) -> int:
    """Retrieve the session ID based on the tracking session name."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT id FROM tracking_sessions WHERE name = ?
            """, (session_name,))
            row = cursor.fetchone()
            if row:
                return row[0]
            logger.error("Session with name '%s' not found.", session_name)
            return -1
    except sqlite3.Error:
        logger.exception("Error retrieving session ID by name")
        return -1

def get_frequencies_by_session(session_name: str) -> list[dict]:
    """Retrieve all frequency data associated with a specific tracking session."""
    session_id = get_session_id_by_name(session_name)
    if session_id == -1:
        return []

    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT frequency, data_type, latitude, longitude, amplitude, timestamp
                FROM frequency_data WHERE session_id = ?
            """, (session_id,))
            frequencies = cursor.fetchall()

            return [
                {
                    "frequency": freq[0],
                    "data_type": freq[1],
                    "latitude": freq[2],
                    "longitude": freq[3],
                    "amplitude": freq[4],
                    "timestamp": freq[5],
                }
                for freq in frequencies
            ]
    except sqlite3.Error:
        logger.exception("Error retrieving frequency data for session")
        return []

def get_all_session_names() -> list[str]:
    """Retrieve all session names from the tracking_sessions table."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT name FROM tracking_sessions ORDER BY date DESC
            """)
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    except sqlite3.Error:
        logger.exception("Error retrieving session names")
        return []
