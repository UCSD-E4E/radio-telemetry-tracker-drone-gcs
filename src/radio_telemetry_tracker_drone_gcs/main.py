"""Main entry point for the RTT Drone GCS application."""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from radio_telemetry_tracker_drone_gcs.comms.communication_bridge import CommunicationBridge
from radio_telemetry_tracker_drone_gcs.services.tile_db import init_db
from radio_telemetry_tracker_drone_gcs.window import MainWindow

logger = logging.getLogger(__name__)

def main() -> int:
    """Start the RTT Drone GCS application."""
    try:
        # Initialize DB (tiles + POIs)
        init_db()

        app = QApplication(sys.argv)
        window = MainWindow()

        # Create bridging object
        bridge = CommunicationBridge()
        window.set_bridge(bridge)

        window.show()
        return app.exec()
    except Exception:
        logger.exception("Failed to initialize DB")
        return 1


if __name__ == "__main__":
    sys.exit(main())
