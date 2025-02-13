import logging
from typing import Any

from radio_telemetry_tracker_drone_gcs.services.frequency_db import (
    add_tracking_session_db,
    init_db,
    list_tracking_sessions_db,
    remove_tracking_session_db,
    add_frequency_db,
    list_frequencies_db,
    remove_frequency_db,
    get_tracking_session_id_by_name,
    get_frequencies_by_tracking_session_id,
)


class FrequencyService:
    """Manages frequency and tracking session retrieval, creation, removal, etc."""

    def __init__(self) -> None:
        """Initialize the Frequency service by initializing the database."""
        init_db()

    def get_tracking_sessions(self) -> list[dict[str, Any]]:
        """Get all tracking sessions from the database."""
        return list_tracking_sessions_db()

    def add_tracking_session(self, name: str, description: str) -> bool:
        """Add a new tracking session to the database.

        Args:
            name: Name of the tracking session
            description: Description of the tracking session

        Returns:
            bool: True if tracking session was added successfully, False otherwise
        """
        try:
            return add_tracking_session_db(name, description)
        except Exception:
            logging.exception("Error adding tracking session")
            return False

    def remove_tracking_session(self, session_id: int) -> bool:
        """Remove a tracking session from the database.

        Args:
            session_id: ID of the tracking session to remove

        Returns:
            bool: True if tracking session was removed successfully, False otherwise
        """
        try:
            return remove_tracking_session_db(session_id)
        except Exception:
            logging.exception("Error removing tracking session")
            return False

    def get_frequencies(self) -> list[dict[str, Any]]:
        """Get all frequency records from the database."""
        return list_frequencies_db()

    def add_frequency(self, frequency: float, signal_strength: float, tracking_session_id: int) -> bool:
        """Add a frequency reading to a tracking session in the database.

        Args:
            frequency: The frequency value (Hz)
            signal_strength: The signal strength value (dB)
            tracking_session_id: The associated tracking session ID

        Returns:
            bool: True if frequency was added successfully, False otherwise
        """
        try:
            return add_frequency_db(frequency, signal_strength, tracking_session_id)
        except Exception:
            logging.exception("Error adding frequency")
            return False

    def remove_frequency(self, frequency_id: int) -> bool:
        """Remove a frequency record from the database.

        Args:
            frequency_id: ID of the frequency record to remove

        Returns:
            bool: True if frequency was removed successfully, False otherwise
        """
        try:
            return remove_frequency_db(frequency_id)
        except Exception:
            logging.exception("Error removing frequency")
            return False
        
    # New method to get frequency data by tracking session name
    def get_frequencies_by_tracking_session_name(self, session_name: str) -> list[dict[str, Any]]:
        """Get frequencies for a tracking session by its name."""
        tracking_session_id = get_tracking_session_id_by_name(session_name)
        if tracking_session_id:
            return get_frequencies_by_tracking_session_id(tracking_session_id)
        return []
