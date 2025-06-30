"""Simulator service for testing and development."""

from __future__ import annotations

import logging
import multiprocessing
from typing import TYPE_CHECKING

from radio_telemetry_tracker_drone_gcs.services.simulator_core import SimulatorCore

if TYPE_CHECKING:
    from radio_telemetry_tracker_drone_comms_package import RadioConfig

logger = logging.getLogger(__name__)


def run_simulator(radio_config: RadioConfig) -> None:
    """Run the simulator in a separate process."""
    try:
        logger.info("Starting simulator core...")
        simulator = SimulatorCore(radio_config)
        simulator.start()
        logger.info("Simulator core started successfully")
        # Keep the process alive
        while True:
            multiprocessing.Event().wait(1.0)
    except Exception:
        logger.exception("Error in simulator process")
    finally:
        if "simulator" in locals():
            try:
                simulator.stop()
                logger.info("Simulator core stopped")
            except Exception:
                logger.exception("Error stopping simulator in process")


class SimulatorService:
    """Controls the simulator instance and manages communication in a separate process."""

    def __init__(self, radio_config: RadioConfig) -> None:
        """Initialize simulator service."""
        self._radio_config = radio_config
        self._process: multiprocessing.Process | None = None

    def start(self) -> None:
        """Start the simulator in a separate process."""
        if self._process is not None:
            msg = "Simulator process already running"
            raise RuntimeError(msg)

        try:
            logger.info("Launching simulator process...")
            self._process = multiprocessing.Process(
                target=run_simulator,
                args=(self._radio_config,),
                daemon=True,
            )
            self._process.start()
            logger.info("Simulator process started successfully")
        except Exception:
            logger.exception("Failed to start simulator process")
            self.stop()
            raise

    def stop(self) -> None:
        """Stop the simulator and clean up resources."""
        if self._process:
            try:
                self._process.terminate()
                self._process.join(timeout=2.0)
                if self._process.is_alive():
                    logger.warning("Simulator process did not stop cleanly, killing...")
                    self._process.kill()
                    self._process.join(timeout=1.0)
            except Exception:
                logger.exception("Error stopping simulator process")

        self._process = None
        logger.info("Simulator stopped")
