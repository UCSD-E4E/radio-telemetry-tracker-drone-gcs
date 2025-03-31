import logging
from typing import Any
from radio_telemetry_tracker_drone_gcs.services.frequency_db import (
    init_db,
    add_tracking_session,
    add_frequency,
    get_session_id_by_name, 
    get_frequencies_by_session, 
    save_frequencies_to_session,
)


class FrequencyService:
    """Manages frequency and tracking session retrieval, creation, removal, etc."""

    def __init__(self) -> None:
        """Initialize the Frequency service by initializing the database."""
        init_db()

    def add_tracking_session(self, name: str, date: str) -> int:
        """Add a new tracking session to the database.

        Args:
            name: Name of the tracking session
            date: Date of the tracking session

        Returns:
            int: The ID of the newly created tracking session
        """
        try:
            return add_tracking_session(name, date)
        except Exception:
            logging.exception("Error adding tracking session")
            return -1

    def add_frequency(self, frequency: int, data_type: str, latitude: float, longitude: float, amplitude: float, session_name: str, timestamp: int) -> bool:
        """Add a frequency record to a specific tracking session.

        Args:
            frequency: Frequency value (Hz)
            data_type: Type of the frequency data ('ping' or 'location_estimate')
            latitude: Latitude of the frequency record
            longitude: Longitude of the frequency record
            amplitude: Amplitude of the frequency
            session_name: Name of the tracking session
            timestamp: Timestamp for the frequency record

        Returns:
            bool: True if the frequency was added successfully, False otherwise
        """
        session_id = get_session_id_by_name(session_name)
        if session_id == -1:
            logging.error(f"Session '{session_name}' not found.")
            return False

        try:
            return add_frequency(frequency, data_type, latitude, longitude, amplitude, session_id, timestamp)
        except Exception:
            logging.exception("Error adding frequency")
            return False

    def save_frequencies_to_session(self, session_name: str, session_date: str, frequencies: list[dict]) -> int:
        """Create a new tracking session and save the frequencies associated with it.

        Args:
            session_name: Name of the tracking session
            session_date: Date of the tracking session
            frequencies: List of frequency data (dict with frequency details)

        Returns:
            int: The ID of the created tracking session or -1 if an error occurred
        """
        try:
            return save_frequencies_to_session(session_name, session_date, frequencies)
        except Exception:
            logging.exception("Error saving frequencies to session")
            return -1

    def get_frequencies_by_session(self, session_name: str) -> list[dict[str, Any]]:
        """Retrieve all frequency records for a specific tracking session.

        Args:
            session_name: Name of the tracking session

        Returns:
            list[dict]: List of frequency data for the session
        """
        try:
            return get_frequencies_by_session(session_name)
        except Exception:
            logging.exception("Error retrieving frequencies for session")
            return []

