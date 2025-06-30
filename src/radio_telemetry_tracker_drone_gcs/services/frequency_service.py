"""Service layer for frequency and tracking session operations."""

import logging
from typing import Any

from radio_telemetry_tracker_drone_gcs.services.frequency_db import (
    add_frequency,
    add_tracking_session,
    get_all_session_names,
    get_frequencies_by_session,
    get_session_id_by_name,
    init_db,
    save_frequencies_to_session,
)


class FrequencyService:
    """Manages frequency and tracking session retrieval, creation, removal, etc."""

    def __init__(self) -> None:
        """Initialize the Frequency service by initializing the database."""
        init_db()

    def add_tracking_session(self, name: str, date: str) -> int:
        """Add a new tracking session to the database."""
        try:
            return add_tracking_session(name, date)
        except Exception:
            logging.exception("Error adding tracking session")
            return -1

    def add_frequency(# noqa: PLR0913
        self,
        frequency: int,
        data_type: str,
        latitude: float,
        longitude: float,
        amplitude: float,
        session_name: str,
        timestamp: int,
    ) -> bool:
        """Add a frequency record to a specific tracking session."""
        session_id = get_session_id_by_name(session_name)
        if session_id == -1:
            logging.error("Session '%s' not found.", session_name)
            return False

        try:
            return add_frequency(frequency, data_type, latitude, longitude, amplitude, session_id, timestamp)
        except Exception:
            logging.exception("Error adding frequency")
            return False

    def save_frequencies_to_session(self, session_name: str, session_date: str, frequencies: list[dict]) -> int:
        """Create a new tracking session and save the frequencies associated with it."""
        try:
            return save_frequencies_to_session(session_name, session_date, frequencies)
        except Exception:
            logging.exception("Error saving frequencies to session")
            return -1

    def get_frequencies_by_session(self, session_name: str) -> list[dict[str, Any]]:
        """Retrieve all frequency records for a specific tracking session."""
        try:
            return get_frequencies_by_session(session_name)
        except Exception:
            logging.exception("Error retrieving frequencies for session")
            return []

    def get_all_session_names(self, _: object = None) -> list[str]:
        """Retrieve all tracking session names."""
        try:
            return get_all_session_names()
        except Exception:
            logging.exception("Error retrieving session names")
            return []
