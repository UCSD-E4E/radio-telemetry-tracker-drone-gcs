import logging
import sqlite3
from contextlib import contextmanager
from typing import Generator, List, Dict

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
                    data_type TEXT NOT NULL,  -- 'ping' or 'location_estimate'
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    amplitude REAL,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES tracking_sessions(id)
                )
            """)

            conn.commit()
    except sqlite3.Error:
        logging.exception("Error initializing database")
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
            return cursor.lastrowid  # Return the ID of the newly created session
    except sqlite3.Error:
        logging.exception("Error adding tracking session")
        return -1

def add_frequency(frequency: int, data_type: str, latitude: float, longitude: float, amplitude: float, session_id: int, timestamp: int) -> bool:
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
        logging.exception("Error adding frequency data")
        return False

def save_frequencies_to_session(session_name: str, session_date: str, frequencies: list[dict]) -> int:
    """
    Create a new tracking session and save the frequencies associated with it.

    :param session_name: The name of the new tracking session
    :param session_date: The date of the new tracking session
    :param frequencies: List of frequency data (dict with frequency details)
    :return: The ID of the created tracking session or -1 if an error occurred
    """
    # 1. Create the tracking session
    session_id = add_tracking_session(session_name, session_date)
    if session_id == -1:
        return -1

    # 2. Save the frequencies to the newly created session
    for freq in frequencies:
        success = add_frequency(
            frequency=freq['frequency'],
            data_type=freq['data_type'],
            latitude=freq['latitude'],
            longitude=freq['longitude'],
            amplitude=freq['amplitude'],
            session_id=session_id,
            timestamp=freq['timestamp']
        )
        if not success:
            logging.error(f"Failed to add frequency data for session {session_name}")
            return -1  # Return failure if any frequency fails to save

    return session_id  # Return the session ID if all frequencies were successfully saved

def get_session_id_by_name(session_name: str) -> int:
    """Retrieve the session ID based on the tracking session name."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT id FROM tracking_sessions WHERE name = ?
            """, (session_name,))
            row = cursor.fetchone()
            if row:
                return row[0]  # Return the session ID
            else:
                logging.error(f"Session with name '{session_name}' not found.")
                return -1  # Return -1 if no session is found
    except sqlite3.Error:
        logging.exception("Error retrieving session ID by name")
        return -1

def get_frequencies_by_session(session_name: str) -> List[Dict]:
    """Retrieve all frequency data associated with a specific tracking session."""
    session_id = get_session_id_by_name(session_name)
    if session_id == -1:
        return []  # Return empty list if the session doesn't exist

    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT frequency, data_type, latitude, longitude, amplitude, timestamp 
                FROM frequency_data WHERE session_id = ?
            """, (session_id,))
            frequencies = cursor.fetchall()
            
            # Convert result to a list of dictionaries
            frequency_data = [
                {
                    "frequency": freq[0],
                    "data_type": freq[1],
                    "latitude": freq[2],
                    "longitude": freq[3],
                    "amplitude": freq[4],
                    "timestamp": freq[5]
                }
                for freq in frequencies
            ]
            
            return frequency_data
    except sqlite3.Error:
        logging.exception("Error retrieving frequency data for session")
        return []  # Return empty list if an error occurs
