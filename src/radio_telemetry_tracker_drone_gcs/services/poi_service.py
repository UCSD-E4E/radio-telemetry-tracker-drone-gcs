"""poi_service.py: higher-level logic for POIs, calls poi_db for CRUD operations."""

import logging
from typing import Any

from radio_telemetry_tracker_drone_gcs.services.poi_db import (
    add_poi_db,
    init_db,
    list_pois_db,
    remove_poi_db,
    rename_poi_db,
)


class PoiService:
    """Manages POI retrieval, creation, removal, rename, etc."""

    def __init__(self) -> None:
        """Initialize the POI service by initializing the database."""
        init_db()

    def get_pois(self) -> list[dict[str, Any]]:
        """Get all POIs from the database."""
        return list_pois_db()

    def add_poi(self, name: str, coords: list[float]) -> bool:
        """Add a new POI to the database.

        Args:
            name: Name of the POI
            coords: List containing [latitude, longitude]

        Returns:
            bool: True if POI was added successfully, False otherwise
        """
        try:
            return add_poi_db(name, coords[0], coords[1])
        except Exception:
            logging.exception("Error adding POI")
            return False

    def remove_poi(self, name: str) -> bool:
        """Remove a POI from the database.

        Args:
            name: Name of the POI to remove

        Returns:
            bool: True if POI was removed successfully, False otherwise
        """
        try:
            return remove_poi_db(name)
        except Exception:
            logging.exception("Error removing POI")
            return False

    def rename_poi(self, old_name: str, new_name: str) -> bool:
        """Rename a POI in the database.

        Args:
            old_name: Current name of the POI
            new_name: New name for the POI

        Returns:
            bool: True if POI was renamed successfully, False otherwise
        """
        try:
            return rename_poi_db(old_name, new_name)
        except Exception:
            logging.exception("Error renaming POI")
            return False
