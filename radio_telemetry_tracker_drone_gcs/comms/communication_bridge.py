"""Bridge module for handling communication between Qt frontend and drone backend.

Provides a Qt-based interface for drone operations, tile management, and POI handling.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

import pyproj
from PyQt6.QtCore import QObject, QTimer, QVariant, pyqtSignal, pyqtSlot
from radio_telemetry_tracker_drone_comms_package import (
    ConfigRequestData,
    ConfigResponseData,
    ErrorData,
    GPSData,
    LocEstData,
    PingData,
    RadioConfig,
    StartResponseData,
    StopResponseData,
    SyncResponseData,
)

from radio_telemetry_tracker_drone_gcs.comms.drone_comms_service import DroneCommsService
from radio_telemetry_tracker_drone_gcs.comms.state_machine import DroneState, DroneStateMachine, StateTransition
from radio_telemetry_tracker_drone_gcs.data.drone_data_manager import DroneDataManager
from radio_telemetry_tracker_drone_gcs.data.models import (
    GpsData as InternalGpsData,
)
from radio_telemetry_tracker_drone_gcs.data.models import (
    LocEstData as InternalLocEstData,
)
from radio_telemetry_tracker_drone_gcs.data.models import (
    PingData as InternalPingData,
)
from radio_telemetry_tracker_drone_gcs.services.poi_service import PoiService
from radio_telemetry_tracker_drone_gcs.services.simulator_service import SimulatorService
from radio_telemetry_tracker_drone_gcs.services.tile_service import TileService
from radio_telemetry_tracker_drone_gcs.services.frequency_service import FrequencyService


logger = logging.getLogger(__name__)


class CommunicationBridge(QObject):
    """Bridge between Qt frontend and drone communications backend, handling all drone-related operations."""

    # Sync/Connect
    sync_success = pyqtSignal(str)
    sync_failure = pyqtSignal(str)
    sync_timeout = pyqtSignal()

    # Config
    config_success = pyqtSignal(str)
    config_failure = pyqtSignal(str)
    config_timeout = pyqtSignal()

    # Start
    start_success = pyqtSignal(str)
    start_failure = pyqtSignal(str)
    start_timeout = pyqtSignal()

    # Stop
    stop_success = pyqtSignal(str)
    stop_failure = pyqtSignal(str)
    stop_timeout = pyqtSignal()

    # Disconnect
    disconnect_success = pyqtSignal(str)
    disconnect_failure = pyqtSignal(str)

    # Fatal error
    fatal_error = pyqtSignal()

    # Tile & POI signals
    tile_info_updated = pyqtSignal(QVariant)
    pois_updated = pyqtSignal(QVariant)

    # GPS, Ping, LocEst
    gps_data_updated = pyqtSignal(QVariant)
    frequency_data_updated = pyqtSignal(QVariant)

    # Simulator
    simulator_started = pyqtSignal()
    simulator_stopped = pyqtSignal()

    #Tracking Sessions 
    tracking_session_updated = pyqtSignal(QVariant)

    def __init__(self) -> None:
        """Initialize the communication bridge with data manager and services."""
        super().__init__()

        self._drone_data_manager = DroneDataManager()
        self._drone_data_manager.gps_data_updated.connect(self.gps_data_updated.emit)
        self._drone_data_manager.frequency_data_updated.connect(self.frequency_data_updated.emit)

        # Tile & POI
        self._tile_service = TileService()
        self._poi_service = PoiService()

        #Tracking Sessions
        self._frequency_service = FrequencyService()

        # State machine
        self._state_machine = DroneStateMachine()
        self._state_machine.state_error.connect(self.fatal_error.emit)
        self._setup_state_handlers()

        # Comms
        self._comms_service: DroneCommsService | None = None
        self._sync_response_received: bool = False
        self._config_response_received: bool = False
        self._start_response_received: bool = False
        self._stop_response_received: bool = False
        self._disconnect_response_received: bool = False

        # Simulator
        self._simulator_service: SimulatorService | None = None

    def _setup_state_handlers(self) -> None:
        """Set up state machine handlers."""
        # Radio config handlers
        self._state_machine.register_transition_handler(
            DroneState.RADIO_CONFIG_WAITING,
            lambda: self._comms_service.register_sync_response_handler(self._on_sync_response, once=True),
        )

        # Ping finder config handlers
        self._state_machine.register_transition_handler(
            DroneState.PING_FINDER_CONFIG_WAITING,
            lambda: self._comms_service.register_config_response_handler(self._on_config_response, once=True),
        )

        # Start handlers
        self._state_machine.register_transition_handler(
            DroneState.START_WAITING,
            lambda: self._comms_service.register_start_response_handler(self._on_start_response, once=True),
        )

        # Stop handlers
        self._state_machine.register_transition_handler(
            DroneState.STOP_WAITING,
            lambda: self._comms_service.register_stop_response_handler(self._on_stop_response, once=True),
        )

        # Register timeout handlers
        self._state_machine.register_timeout_handler(
            DroneState.RADIO_CONFIG_WAITING,
            lambda: self.sync_timeout.emit(),
        )
        self._state_machine.register_timeout_handler(
            DroneState.PING_FINDER_CONFIG_WAITING,
            lambda: self.config_timeout.emit(),
        )
        self._state_machine.register_timeout_handler(
            DroneState.START_WAITING,
            lambda: self.start_timeout.emit(),
        )
        self._state_machine.register_timeout_handler(
            DroneState.STOP_WAITING,
            lambda: self.stop_timeout.emit(),
        )

    # --------------------------------------------------------------------------
    # Basic slots for comms
    # --------------------------------------------------------------------------

    @pyqtSlot(result="QVariantList")
    def get_serial_ports(self) -> list[str]:
        """Return a list of available serial port device names."""
        import serial.tools.list_ports

        port_info = list(serial.tools.list_ports.comports())
        return [str(p.device) for p in port_info]

    @pyqtSlot("QVariantMap", result=bool)
    def initialize_comms(self, config: dict[str, Any]) -> bool:
        """Initialize drone communications with the given configuration.

        Args:
            config: Dictionary containing radio and acknowledgment settings.

        Returns:
            bool: True if initialization succeeded, False otherwise.
        """
        try:
            radio_cfg = RadioConfig(
                interface_type=config["interface_type"],
                port=config["port"],
                baudrate=int(config["baudrate"]),
                host=config["host"],
                tcp_port=int(config["tcp_port"]),
                server_mode=False,
            )
            ack_s = float(config["ack_timeout"])
            max_r = int(config["max_retries"])

            self._comms_service = DroneCommsService(
                radio_config=radio_cfg,
                ack_timeout=ack_s,
                max_retries=max_r,
                on_ack_success=self._on_ack_success,
                on_ack_timeout=self._on_ack_timeout,
            )
            self._comms_service.start()

            # Register packet handlers
            self._comms_service.register_error_handler(self._handle_error_packet)

            # Transition to connecting state
            self._state_machine.transition_to(
                DroneState.RADIO_CONFIG_WAITING,
                StateTransition(
                    from_state=DroneState.RADIO_CONFIG_INPUT,
                    to_state=DroneState.RADIO_CONFIG_WAITING,
                    success_message="Drone connected successfully",
                    failure_message="Failed to connect to drone",
                ),
            )

            # Send sync
            self._comms_service.send_sync_request()
            self._sync_response_received = False

            tt = ack_s * max_r
            QTimer.singleShot(int(tt * 1000), self._sync_timeout_check)
        except Exception as e:
            logging.exception("Error in initialize_comms")
            self.sync_failure.emit(f"Initialize comms failed: {e!s}")
            return False
        else:
            return True

    @pyqtSlot()
    def cancel_connection(self) -> None:
        """User cancels sync/connect attempt."""
        if self._comms_service:
            self._comms_service.stop()
            self._comms_service = None
            self._state_machine.transition_to(DroneState.RADIO_CONFIG_INPUT)

    @pyqtSlot()
    def disconnect(self) -> None:
        """Disconnect from the drone and clean up communication resources."""
        if not self._comms_service:
            self.disconnect_success.emit("UNDEFINED BEHAVIOR: Not Connected.")
            return
        try:
            self._comms_service.register_stop_response_handler(self._on_disconnect_response, once=True)
            self._comms_service.send_stop_request()
            self._disconnect_response_received = False

            tt = self._comms_service.ack_timeout * self._comms_service.max_retries
            QTimer.singleShot(int(tt * 1000), self._disconnect_timeout_check)
        except Exception:
            logging.exception("Stop request failed => forcing cleanup.")
            self.disconnect_failure.emit("Stop request failed... forcing cleanup.")
            self._cleanup()

    # --------------------------------------------------------------------------
    # Config
    # --------------------------------------------------------------------------
    @pyqtSlot("QVariantMap", result=bool)
    def send_config_request(self, cfg: dict[str, Any]) -> bool:
        """Send config => wait => user can cancel => if ack fails => config_timout."""
        if not self._comms_service:
            self.config_failure.emit("UNDEFINED BEHAVIOR: Not Connected.")
            return False

        try:
            req = ConfigRequestData(
                gain=float(cfg["gain"]),
                sampling_rate=int(cfg["sampling_rate"]),
                center_frequency=int(cfg["center_frequency"]),
                run_num=int(time.time()),
                enable_test_data=bool(cfg["enable_test_data"]),
                ping_width_ms=int(cfg["ping_width_ms"]),
                ping_min_snr=int(cfg["ping_min_snr"]),
                ping_max_len_mult=float(cfg["ping_max_len_mult"]),
                ping_min_len_mult=float(cfg["ping_min_len_mult"]),
                target_frequencies=list(map(int, cfg["target_frequencies"])),
            )
            self._comms_service.register_config_response_handler(self._on_config_response, once=True)
            self._comms_service.send_config_request(req)
            self._config_response_received = False

            tt = self._comms_service.ack_timeout * self._comms_service.max_retries
            QTimer.singleShot(int(tt * 1000), self._config_timeout_check)
        except Exception as e:
            logging.exception("Error in send_config_request")
            self.config_failure.emit(str(e))
            return False
        else:
            return True

    @pyqtSlot(result=bool)
    def cancel_config_request(self) -> bool:
        """Cancel the config request."""
        if not self._comms_service:
            self.config_failure.emit("UNDEFINED BEHAVIOR: Not Connected.")
            return False
        self._comms_service.unregister_config_response_handler(self._on_config_response)
        return True

    # --------------------------------------------------------------------------
    # Start
    # --------------------------------------------------------------------------
    @pyqtSlot(result=bool)
    def send_start_request(self) -> bool:
        """Send start request => wait => user can cancel => if ack fails => start_timeout."""
        if not self._comms_service:
            self.start_failure.emit("UNDEFINED BEHAVIOR: Not Connected.")
            return False

        try:
            self._comms_service.register_start_response_handler(self._on_start_response, once=True)
            self._comms_service.send_start_request()
            self._start_response_received = False

            tt = self._comms_service.ack_timeout * self._comms_service.max_retries
            QTimer.singleShot(int(tt * 1000), self._start_timeout_check)
        except Exception as e:
            logging.exception("Error in send_start_request")
            self.start_failure.emit(str(e))
            return False
        else:
            return True

    @pyqtSlot(result=bool)
    def cancel_start_request(self) -> bool:
        """Cancel the start request."""
        if not self._comms_service:
            self.start_failure.emit("UNDEFINED BEHAVIOR: Not Connected.")
            return False
        self._comms_service.unregister_start_response_handler(self._on_start_response)
        return True

    # --------------------------------------------------------------------------
    # Stop
    # --------------------------------------------------------------------------
    @pyqtSlot(result=bool)
    def send_stop_request(self) -> bool:
        """Send stop request => wait => user can cancel => if ack fails => stop_timeout."""
        if not self._comms_service:
            self.stop_failure.emit("UNDEFINED BEHAVIOR: Not Connected.")
            return False

        try:
            self._comms_service.register_stop_response_handler(self._on_stop_response, once=True)
            self._comms_service.send_stop_request()
            self._stop_response_received = False

            tt = self._comms_service.ack_timeout * self._comms_service.max_retries
            QTimer.singleShot(int(tt * 1000), self._stop_timeout_check)
        except Exception as e:
            logging.exception("Error in send_stop_request")
            self.stop_failure.emit(str(e))
            return False
        else:
            return True

    @pyqtSlot(result=bool)
    def cancel_stop_request(self) -> bool:
        """Cancel the stop request."""
        if not self._comms_service:
            self.stop_failure.emit("UNDEFINED BEHAVIOR: Not Connected.")
            return False
        self._comms_service.unregister_stop_response_handler(self._on_stop_response)
        return True

    # --------------------------------------------------------------------------
    # GPS, Ping, LocEst
    # --------------------------------------------------------------------------
    def _handle_gps_data(self, gps: GPSData) -> None:
        lat, lng = self._transform_coords(gps.easting, gps.northing, gps.epsg_code)
        internal_gps = InternalGpsData(
            lat=lat,
            long=lng,
            altitude=gps.altitude,
            heading=gps.heading,
            timestamp=gps.timestamp,
            packet_id=gps.packet_id,
        )
        self._drone_data_manager.update_gps(internal_gps)

    def _handle_ping_data(self, ping: PingData) -> None:
        """Handle ping data from drone."""
        try:
            # Validate ping data
            if not all(
                hasattr(ping, attr)
                for attr in ["easting", "northing", "epsg_code", "frequency", "amplitude", "timestamp", "packet_id"]
            ):
                logger.error("Invalid ping data received: missing required attributes")
                return

            lat, lng = self._transform_coords(ping.easting, ping.northing, ping.epsg_code)
            logger.info(
                "Ping data received - Freq: %d Hz, Amplitude: %.2f dB, UTM: (%.2f, %.2f) -> LatLng: (%.6f, %.6f)",
                ping.frequency,
                ping.amplitude,
                ping.easting,
                ping.northing,
                lat,
                lng,
            )
            internal_ping = InternalPingData(
                frequency=ping.frequency,
                amplitude=ping.amplitude,
                lat=lat,
                long=lng,
                timestamp=ping.timestamp,
                packet_id=ping.packet_id,
            )
            self._drone_data_manager.add_ping(internal_ping)
        except Exception:
            logger.exception("Error handling ping data")

    def _handle_loc_est_data(self, loc_est: LocEstData) -> None:
        """Handle location estimate data from drone."""
        lat, lng = self._transform_coords(loc_est.easting, loc_est.northing, loc_est.epsg_code)
        internal_loc_est = InternalLocEstData(
            frequency=loc_est.frequency,
            lat=lat,
            long=lng,
            timestamp=loc_est.timestamp,
            packet_id=loc_est.packet_id,
        )
        logger.info(
            "Location estimate received - Freq: %d Hz, Position: (%.6f, %.6f)",
            loc_est.frequency,
            lat,
            lng,
        )
        self._drone_data_manager.update_loc_est(internal_loc_est)

    # --------------------------------------------------------------------------
    # Error
    # --------------------------------------------------------------------------
    def _handle_error_packet(self, _: ErrorData) -> None:
        logging.error("Received fatal error packet")
        self.fatal_error.emit()

    # --------------------------------------------------------------------------
    # Tile & POI bridging
    # --------------------------------------------------------------------------
    @pyqtSlot("int", "int", "int", "QString", "QVariantMap", result="QString")
    def get_tile(self, z: int, x: int, y: int, source: str, options: dict) -> str:
        """Get map tile data for the specified coordinates and zoom level.

        Args:
            z: Zoom level
            x: X coordinate
            y: Y coordinate
            source: Tile source identifier
            options: Additional options including offline mode

        Returns:
            Base64 encoded tile data or empty string on error
        """
        try:
            offline = bool(options["offline"])
            tile_data = self._tile_service.get_tile(z, x, y, source_id=source, offline=offline)
            if not tile_data:
                return ""
            # We can update tile info
            info = self._tile_service.get_tile_info()
            self.tile_info_updated.emit(QVariant(info))
            return base64.b64encode(tile_data).decode("utf-8")
        except Exception:
            logging.exception("Error in get_tile()")
            return ""

    @pyqtSlot(result=QVariant)
    def get_tile_info(self) -> QVariant:
        """Get information about the current tile cache state."""
        try:
            info = self._tile_service.get_tile_info()
            return QVariant(info)
        except Exception:
            logging.exception("Error in get_tile_info()")
            return QVariant({})

    @pyqtSlot(result=bool)
    def clear_tile_cache(self) -> bool:
        """Clear the map tile cache and return success status."""
        try:
            return self._tile_service.clear_tile_cache()
        except Exception:
            logging.exception("Error clearing tile cache")
            return False

    @pyqtSlot(result="QVariant")
    def get_pois(self) -> list[dict]:
        """Get list of all points of interest (POIs) in the system."""
        try:
            return self._poi_service.get_pois()
        except Exception:
            logging.exception("Error getting POIs")
            return []

    @pyqtSlot(str, "QVariantList", result=bool)
    def add_poi(self, name: str, coords: list[float]) -> bool:
        """Add a new point of interest with the given name and coordinates."""
        try:
            self._poi_service.add_poi(name, coords)
            self._emit_pois()
        except Exception:
            logging.exception("Error adding POI")
            return False
        else:
            return True

    @pyqtSlot(str, result=bool)
    def remove_poi(self, name: str) -> bool:
        """Remove a point of interest with the specified name."""
        try:
            self._poi_service.remove_poi(name)
            self._emit_pois()
        except Exception:
            logging.exception("Error removing POI")
            return False
        else:
            return True

    @pyqtSlot(str, str, result=bool)
    def rename_poi(self, old_name: str, new_name: str) -> bool:
        """Rename a point of interest from old_name to new_name."""
        try:
            self._poi_service.rename_poi(old_name, new_name)
            self._emit_pois()
        except Exception:
            logging.exception("Error renaming POI")
            return False
        else:
            return True

    def _emit_pois(self) -> None:
        pois = self._poi_service.get_pois()
        self.pois_updated.emit(QVariant(pois))

    # --------------------------------------------------------------------------
    # Frequency and Tracking Session Bridging
    # --------------------------------------------------------------------------
   
    # Slot to add a tracking session
    @pyqtSlot(str, str, result=bool)
    def add_tracking_session(self, name: str, description: str) -> bool:
        """Add a new tracking session."""
        try:
            # Add the tracking session through FrequencyService
            success = self._frequency_service.add_tracking_session(name, description)
            if success:
                self.tracking_session_updated.emit(QVariant(self._frequency_service.get_tracking_sessions()))
            return success
        except Exception:
            logging.exception("Error adding tracking session")
            return False

    # Slot to remove a tracking session
    @pyqtSlot(int, result=bool)
    def remove_tracking_session(self, session_id: int) -> bool:
        """Remove a tracking session."""
        try:
            # Remove the tracking session through FrequencyService
            success = self._frequency_service.remove_tracking_session(session_id)
            if success:
                self.tracking_session_updated.emit(QVariant(self._frequency_service.get_tracking_sessions()))
            return success
        except Exception:
            logging.exception("Error removing tracking session")
            return False

    # Slot to add a frequency reading to a tracking session
    @pyqtSlot(float, float, int, result=bool)
    def add_frequency(self, frequency: float, signal_strength: float, tracking_session_id: int) -> bool:
        """Add a frequency reading to the specified tracking session."""
        try:
            success = self._frequency_service.add_frequency(frequency, signal_strength, tracking_session_id)
            if success:
                # Optionally, emit updated frequency data if needed
                self.frequency_data_updated.emit(QVariant(self._frequency_service.get_frequencies()))
            return success
        except Exception:
            logging.exception("Error adding frequency")
            return False

    # Slot to remove a frequency from a tracking session
    @pyqtSlot(int, result=bool)
    def remove_frequency(self, frequency_id: int) -> bool:
        """Remove a frequency reading by its ID."""
        try:
            success = self._frequency_service.remove_frequency(frequency_id)
            if success:
                # Optionally, emit updated frequency data if needed
                self.frequency_data_updated.emit(QVariant(self._frequency_service.get_frequencies()))
            return success
        except Exception:
            logging.exception("Error removing frequency")
            return False
        
    @pyqtSlot(str, result=list)
    def get_frequencies_by_session_name(self, session_name: str) -> list:
        """Get frequencies for a tracking session by its name."""
        try:
            frequencies = self._frequency_service.get_frequencies_by_tracking_session_name(session_name)
            return frequencies  # Return the list of frequencies
        except Exception:
            logging.exception("Error retrieving frequencies for session: %s", session_name)
            return []
    
    # --------------------------------------------------------------------------
    # LAYERS
    # --------------------------------------------------------------------------
    @pyqtSlot(int, result=bool)
    def clear_frequency_data(self, frequency: int) -> bool:
        """Clear all data for the specified frequency and return success status."""
        try:
            self._drone_data_manager.clear_frequency_data(frequency)
        except Exception:
            logging.exception("Error clearing frequency data")
            return False
        else:
            return True

    @pyqtSlot(int, result=bool)
    def clear_all_frequency_data(self) -> bool:
        """Clear all frequency-related data across all frequencies and return success status."""
        try:
            self._drone_data_manager.clear_all_frequency_data()
        except Exception:
            logging.exception("Error clearing all frequency data")
            return False
        else:
            return True

    # --------------------------------------------------------------------------
    # TIMEOUTS
    # --------------------------------------------------------------------------
    def _sync_timeout_check(self) -> None:
        if not self._sync_response_received:
            logging.warning("Sync response not received => sync_timeout.")
            self.sync_timeout.emit()
            self._sync_response_received = True

    def _config_timeout_check(self) -> None:
        if not self._config_response_received:
            logging.warning("Config response not received => config_timeout.")
            self.config_timeout.emit()
            self._config_response_received = True

    def _start_timeout_check(self) -> None:
        if not self._start_response_received:
            logging.warning("Start response not received => start_timeout.")
            self.start_timeout.emit()
            self._start_response_received = True

    def _stop_timeout_check(self) -> None:
        if not self._stop_response_received:
            logging.warning("Stop response not received => stop_timeout.")
            self.stop_timeout.emit()
            self._stop_response_received = True

    def _disconnect_timeout_check(self) -> None:
        if not self._disconnect_response_received:
            logging.warning("Stop response not received => forcibly cleanup => disconnect_timeout.")
            self.disconnect_failure.emit("Stop response not received => forcibly cleanup => disconnect_timeout.")
            self._cleanup()
            self._disconnect_response_received = True

    # --------------------------------------------------------------------------
    # RESPONSES
    # --------------------------------------------------------------------------
    def _on_sync_response(self, rsp: SyncResponseData) -> None:
        """Handle sync response from drone."""
        self._sync_response_received = True

        if not rsp.success:
            logging.warning("Sync success=False => Undefined behavior")
            self.sync_failure.emit("UNDEFINED BEHAVIOR: Sync failed.")
            self._state_machine.transition_to(DroneState.ERROR)
            return

        self.sync_success.emit("Successfully connected to drone.")
        self._comms_service.register_gps_handler(self._handle_gps_data, once=False)
        self._state_machine.transition_to(DroneState.PING_FINDER_CONFIG_INPUT)

    def _on_config_response(self, rsp: ConfigResponseData) -> None:
        """Handle config response from drone."""
        self._config_response_received = True

        if not rsp.success:
            logging.warning("Config success=False => Undefined behavior")
            self.config_failure.emit("UNDEFINED BEHAVIOR: Config failed.")
            self._state_machine.transition_to(DroneState.ERROR)
            return

        self.config_success.emit("Config sent to drone.")
        self._state_machine.transition_to(DroneState.START_INPUT)

    def _on_start_response(self, rsp: StartResponseData) -> None:
        """Handle start response from drone."""
        self._start_response_received = True

        if not rsp.success:
            logging.warning("Start success=False => Improper state.")
            self.start_failure.emit("UNDEFINED BEHAVIOR: Improper state.")
            self._state_machine.transition_to(DroneState.ERROR)
            return

        self.start_success.emit("Drone is now starting.")
        self._comms_service.register_ping_handler(self._handle_ping_data, once=False)
        self._comms_service.register_loc_est_handler(self._handle_loc_est_data, once=False)
        self._state_machine.transition_to(DroneState.STOP_INPUT)

    def _on_stop_response(self, rsp: StopResponseData) -> None:
        """Handle stop response from drone."""
        self._stop_response_received = True

        if not rsp.success:
            logging.warning("Stop success=False => Improper state.")
            self.stop_failure.emit("UNDEFINED BEHAVIOR: Improper state.")
            self._state_machine.transition_to(DroneState.ERROR)
            return

        self.stop_success.emit("Drone is now stopping.")
        self._comms_service.unregister_ping_handler(self._handle_ping_data)
        self._comms_service.unregister_loc_est_handler(self._handle_loc_est_data)
        self._state_machine.transition_to(DroneState.PING_FINDER_CONFIG_INPUT)

    def _on_disconnect_response(self, rsp: StopResponseData) -> None:
        """Handle disconnect response from drone."""
        self._disconnect_response_received = True

        if not rsp.success:
            logging.warning("Disconnect success=False => Improper state.")
            self.disconnect_failure.emit("UNDEFINED BEHAVIOR: Improper state.")
            self._state_machine.transition_to(DroneState.ERROR)
            return

        self.disconnect_success.emit("Drone is now disconnected.")
        self._comms_service.unregister_gps_handler(self._handle_gps_data)
        self._cleanup()
        self._state_machine.transition_to(DroneState.RADIO_CONFIG_INPUT)

    # --------------------------------------------------------------------------
    # Ack callbacks from DroneComms
    # --------------------------------------------------------------------------
    def _on_ack_success(self, packet_id: int) -> None:
        logging.info("Packet %d ack success", packet_id)

    def _on_ack_timeout(self, packet_id: int) -> None:
        logging.warning("Ack timeout for packet %d", packet_id)

    # --------------------------------------------------------------------------
    # UTILS
    # --------------------------------------------------------------------------
    def _cleanup(self) -> None:
        if self._comms_service:
            self._comms_service.stop()
            self._comms_service = None
        self._state_machine.transition_to(DroneState.RADIO_CONFIG_INPUT)
        self.disconnect_success.emit("Disconnected")

    def _transform_coords(self, easting: float, northing: float, epsg_code: int) -> tuple[float, float]:
        epsg_str = str(epsg_code)
        zone = epsg_str[-2:]
        hemisphere = "north" if epsg_str[-3] == "6" else "south"

        utm_proj = pyproj.Proj(proj="utm", zone=zone, ellps="WGS84", hemisphere=hemisphere)
        wgs84_proj = pyproj.Proj("epsg:4326")
        transformer = pyproj.Transformer.from_proj(utm_proj, wgs84_proj, always_xy=True)
        lng, lat = transformer.transform(easting, northing)
        return (lat, lng)

    # Add logging method to match TypeScript interface
    @pyqtSlot(str)
    def log_message(self, message: str) -> None:
        """Log a message from the frontend."""
        logging.info("Frontend log: %s", message)

    # --------------------------------------------------------------------------
    # SIMULATOR
    # --------------------------------------------------------------------------
    @pyqtSlot("QVariantMap", result=bool)
    def init_simulator(self, config: dict[str, Any]) -> bool:
        """Initialize the simulator with the given radio configuration.

        Args:
            config: Dictionary containing radio configuration settings.

        Returns:
            bool: True if initialization succeeded, False otherwise.
        """
        try:
            # Create radio config for simulator (server mode)
            radio_cfg = RadioConfig(
                interface_type=config["interface_type"],
                port=config["port"],
                baudrate=int(config["baudrate"]),
                host=config["host"],
                tcp_port=int(config["tcp_port"]),
                server_mode=True,  # Simulator acts as server
            )

            # Initialize simulator service
            self._simulator_service = SimulatorService(radio_cfg)
            self._simulator_service.start()
            self.simulator_started.emit()
        except Exception:
            logging.exception("Error initializing simulator")
            return False
        else:
            return True

    @pyqtSlot(result=bool)
    def cleanup_simulator(self) -> bool:
        """Stop the simulator and clean up resources.

        Returns:
            bool: True if cleanup succeeded, False if simulator was not running.
        """
        if not self._simulator_service:
            return False

        try:
            self._simulator_service.stop()
            self._simulator_service = None
            self.simulator_stopped.emit()
        except Exception:
            logging.exception("Error cleaning up simulator")
            return False
        else:
            return True
