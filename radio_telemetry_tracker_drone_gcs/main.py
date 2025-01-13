"""Main entry point for the RTT Drone GCS application."""

import sys

from PyQt6.QtWidgets import QApplication

from radio_telemetry_tracker_drone_gcs.comms.communication_bridge import CommunicationBridge
from radio_telemetry_tracker_drone_gcs.services.tile_db import init_db
from radio_telemetry_tracker_drone_gcs.window import MainWindow


def main() -> int:
    """Start the RTT Drone GCS application."""
    # Initialize DB (tiles + POIs)
    init_db()

    app = QApplication(sys.argv)
    window = MainWindow()

    # Create bridging object
    bridge = CommunicationBridge()
    window.set_bridge(bridge)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
