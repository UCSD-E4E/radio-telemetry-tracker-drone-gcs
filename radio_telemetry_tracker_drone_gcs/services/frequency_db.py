import logging
import sqlite3
from contextlib import contextmanager
from typing import Generator

from radio_telemetry_tracker_drone_gcs.utils.paths import get_db_path

DB_PATH = get_db_path()

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
    """Initialize the database with tables for tracking sessions and frequencies."""
    try:
        with get_db_connection() as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")

            # Drop existing tables if they exist
            conn.execute("DROP TABLE IF EXISTS tracking_sessions")
            conn.execute("DROP TABLE IF EXISTS frequencies")

            # Create tracking_sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracking_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create frequencies table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS frequencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    frequency REAL NOT NULL,
                    signal_strength REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    tracking_session_id INTEGER,
                    FOREIGN KEY (tracking_session_id) REFERENCES tracking_sessions(id)
                )
            """)

            # Add trigger to update tracking_sessions updated_at timestamp
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_tracking_session_timestamp
                AFTER UPDATE ON tracking_sessions
                BEGIN
                    UPDATE tracking_sessions SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.id;
                END;
            """)

            conn.commit()
    except sqlite3.Error:
        logging.exception("Error initializing database")
        raise

def add_tracking_session_db(name: str, description: str) -> bool:
    """Add a new tracking session."""
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO tracking_sessions (name, description) VALUES (?, ?)", (name, description))
            conn.commit()
            return True
    except sqlite3.Error:
        logging.exception("Error adding tracking session")
        return False

def list_tracking_sessions_db() -> list[dict]:
    """Retrieve all tracking sessions."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT id, name, description FROM tracking_sessions ORDER BY created_at")
            return [{"id": id, "name": name, "description": description} for id, name, description in cursor]
    except sqlite3.Error:
        logging.exception("Error listing tracking sessions")
        return []

def remove_tracking_session_db(id: int) -> bool:
    """Remove a tracking session."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM tracking_sessions WHERE id = ?", (id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error:
        logging.exception("Error removing tracking session")
        return False

def add_frequency_db(frequency: float, signal_strength: float, tracking_session_id: int) -> bool:
    """Add a frequency reading to the database."""
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO frequencies (frequency, signal_strength, tracking_session_id) VALUES (?, ?, ?)",
                         (frequency, signal_strength, tracking_session_id))
            conn.commit()
            return True
    except sqlite3.Error:
        logging.exception("Error adding frequency")
        return False

def list_frequencies_db() -> list[dict]:
    """Retrieve all frequency records."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT id, frequency, signal_strength, timestamp, tracking_session_id FROM frequencies ORDER BY timestamp")
            return [{"id": id, "frequency": frequency, "signal_strength": signal_strength, "timestamp": timestamp, "tracking_session_id": tracking_session_id}
                    for id, frequency, signal_strength, timestamp, tracking_session_id in cursor]
    except sqlite3.Error:
        logging.exception("Error listing frequencies")
        return []

def remove_frequency_db(id: int) -> bool:
    """Remove a frequency record."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM frequencies WHERE id = ?", (id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error:
        logging.exception("Error removing frequency")
        return False
    
# Function to get tracking session ID by its name
def get_tracking_session_id_by_name(name: str) -> int:
    """Retrieve the ID of a tracking session by its name."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT id FROM tracking_sessions WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None  # Return None if no session found
    except sqlite3.Error:
        logging.exception("Error retrieving tracking session by name")
        return None

# Function to get all frequencies for a specific tracking session by its ID
def get_frequencies_by_tracking_session_id(tracking_session_id: int) -> list[dict]:
    """Retrieve all frequencies for a specific tracking session."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT id, frequency, signal_strength, timestamp
                FROM frequencies
                WHERE tracking_session_id = ?
                ORDER BY timestamp
            """, (tracking_session_id,))
            return [{"id": id, "frequency": frequency, "signal_strength": signal_strength, "timestamp": timestamp}
                    for id, frequency, signal_strength, timestamp in cursor]
    except sqlite3.Error:
        logging.exception("Error retrieving frequencies for tracking session ID %d", tracking_session_id)
        return []

