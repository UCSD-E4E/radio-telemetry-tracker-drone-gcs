"""Utility functions for managing application paths."""

import os
import sys
from pathlib import Path

APP_NAME = "Radio Telemetry Tracker Drone Ground Control Station"
APP_DIR_NAME = "RTT-Drone-GCS"  # Used for filesystem paths


def get_app_dir() -> Path:
    """Get the application directory based on environment.

    Returns:
        Path: The application directory where persistent files should be stored
    """
    if getattr(sys, "frozen", False):
        # We're running in a bundle
        if sys.platform == "win32":
            return Path(os.environ["LOCALAPPDATA"]) / APP_DIR_NAME
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
        # Linux and other Unix
        return Path.home() / ".local" / "share" / APP_DIR_NAME.lower()
    # We're running in development
    return Path(__file__).parent.parent.parent


def ensure_app_dir() -> None:
    """Create application directory if it doesn't exist."""
    app_dir = get_app_dir()
    app_dir.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    """Get the database file path.

    Returns:
        Path: Path to the SQLite database file
    """
    return get_app_dir() / "rtt_drone_gcs.db"
