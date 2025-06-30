"""Development script for running the application.

Automatically builds the frontend, then runs the Python main entry point.
"""

import sys

from radio_telemetry_tracker_drone_gcs.main import main as app_main

from .utils import build_frontend


def main() -> int:
    """Build frontend and run the app in development mode."""
    build_frontend()
    return app_main()


if __name__ == "__main__":
    sys.exit(main())
