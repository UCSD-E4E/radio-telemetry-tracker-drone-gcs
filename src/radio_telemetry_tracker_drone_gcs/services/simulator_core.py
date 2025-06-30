"""Simulator core module for the Radio Telemetry Tracker drone GCS."""

from __future__ import annotations

import datetime as dt
import logging
import math
import random
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
import pyproj
from radio_telemetry_tracker_drone_comms_package import (
    ConfigRequestData,
    ConfigResponseData,
    DroneComms,
    ErrorData,
    GPSData,
    LocEstData,
    PingData,
    RadioConfig,
    StartRequestData,
    StartResponseData,
    StopRequestData,
    StopResponseData,
    SyncRequestData,
    SyncResponseData,
)
from scipy.optimize import least_squares

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

logger = logging.getLogger(__name__)


class DroneState(Enum):
    """Represents the current state of the drone."""

    IDLE = "IDLE"
    TAKEOFF = "TAKEOFF"
    FLYING = "FLYING"
    RETURNING = "RETURNING"
    LANDING = "LANDING"


@dataclass
class WayPoint:
    """Represents a waypoint in UTM coordinates."""

    easting: float
    northing: float
    altitude: float


class GpsDataGenerator:
    """Generates GPS data for the simulator."""

    def __init__(self) -> None:
        """Initialize the GPS data generator with starting parameters."""
        # UTM zone parameters
        self.zone: str = "11S"
        self.hemisphere: str = "north"

        # Create UTM and WGS84 transformers
        self.utm_proj = pyproj.Proj(proj="utm", zone=11, ellps="WGS84", hemisphere="north")
        self.wgs84_proj = pyproj.Proj("epsg:4326")
        self.transformer = pyproj.Transformer.from_proj(self.utm_proj, self.wgs84_proj, always_xy=True)

        # Starting position (UTM coordinates)
        self.start_point = WayPoint(489276.681, 3611282.577, 2.0)
        self.end_point = WayPoint(489504.058, 3611478.990, 2.0)

        # Flight parameters
        self.target_altitude: float = 30.0  # meters
        self.vertical_speed: float = 2.0  # m/s
        self.horizontal_speed: float = 5.0  # m/s
        self.waypoint_radius: float = 5.0  # meters
        self.update_rate: int = 5  # Hz

        # State variables
        self.current_state: DroneState = DroneState.IDLE
        self.current_position = WayPoint(self.start_point.easting, self.start_point.northing, self.start_point.altitude)
        self.current_heading: float = 0.0
        self.waypoints: list[WayPoint] = []
        self.current_waypoint_idx: int = 0
        self.packet_id: int = 0

        # GPS noise parameters
        self.position_noise_std: float = 0.3  # meters (typical GPS accuracy)
        self.altitude_noise_std: float = 0.5  # meters (altitude is typically less accurate)

        # Thread control
        self._running: bool = False
        self._update_thread: threading.Thread | None = None
        self._last_update: float = time.time()
        self._rng = random.SystemRandom()

        # Generate lawnmower pattern waypoints
        self._generate_lawnmower_pattern()

    def _generate_lawnmower_pattern(self) -> None:
        """Generate waypoints for a lawnmower pattern."""
        # Calculate box dimensions
        height = self.end_point.northing - self.start_point.northing

        # Use 30m spacing between passes
        spacing = 20.0  # meters
        num_passes = max(2, int(height / spacing) + 1)

        # Generate waypoints
        self.waypoints = []

        # Add takeoff point
        self.waypoints.append(WayPoint(self.start_point.easting, self.start_point.northing, self.target_altitude))

        # Generate lawnmower pattern
        for i in range(num_passes):
            northing = self.start_point.northing + i * spacing

            # Add points for each pass
            if i % 2 == 0:
                # Left to right
                self.waypoints.append(WayPoint(self.start_point.easting, northing, self.target_altitude))
                self.waypoints.append(WayPoint(self.end_point.easting, northing, self.target_altitude))
            else:
                # Right to left
                self.waypoints.append(WayPoint(self.end_point.easting, northing, self.target_altitude))
                self.waypoints.append(WayPoint(self.start_point.easting, northing, self.target_altitude))

    def _add_gps_noise(self, easting: float, northing: float, altitude: float) -> tuple[float, float, float]:
        """Add realistic GPS noise to position."""
        noisy_easting = easting + self._rng.gauss(0, self.position_noise_std)
        noisy_northing = northing + self._rng.gauss(0, self.position_noise_std)
        noisy_altitude = altitude + self._rng.gauss(0, self.altitude_noise_std)
        return noisy_easting, noisy_northing, noisy_altitude

    def _calculate_heading(self, current: WayPoint, target: WayPoint) -> float:
        """Calculate heading angle in degrees from current position to target.

        North = 0°, East = 90°, South = 180°, West = 270°.
        """
        dx = target.easting - current.easting
        dy = target.northing - current.northing
        heading = 90 - math.degrees(math.atan2(dy, dx))  # Convert from math angle to compass heading
        return heading % 360

    def _move_towards_waypoint(self, current: WayPoint, target: WayPoint, dt: float) -> WayPoint:
        """Move from current position towards target waypoint."""
        dx = target.easting - current.easting
        dy = target.northing - current.northing
        dz = target.altitude - current.altitude

        # Calculate distances
        horizontal_dist = math.sqrt(dx * dx + dy * dy)

        # Calculate movement distances for this timestep
        max_horiz_dist = self.horizontal_speed * dt
        max_vert_dist = self.vertical_speed * dt

        # Calculate scaling factors
        horiz_scale = min(1.0, max_horiz_dist / horizontal_dist) if horizontal_dist > 0 else 0
        vert_scale = min(1.0, max_vert_dist / abs(dz)) if dz != 0 else 0

        # Calculate new position
        new_easting = current.easting + dx * horiz_scale
        new_northing = current.northing + dy * horiz_scale
        new_altitude = current.altitude + dz * vert_scale

        return WayPoint(new_easting, new_northing, new_altitude)

    def _is_at_waypoint(self, current: WayPoint, target: WayPoint) -> bool:
        """Check if we've reached the target waypoint."""
        dx = target.easting - current.easting
        dy = target.northing - current.northing
        dz = target.altitude - current.altitude

        horizontal_dist = math.sqrt(dx * dx + dy * dy)
        return horizontal_dist < self.waypoint_radius and abs(dz) < 1.0

    def _handle_idle_state(self, dt: float) -> None:
        """Handle IDLE state."""

    def _handle_takeoff_state(self, dt: float) -> None:
        """Handle TAKEOFF state."""
        target = self.waypoints[0]
        self.current_position = self._move_towards_waypoint(self.current_position, target, dt)
        self.current_heading = self._calculate_heading(self.current_position, target)

        if self._is_at_waypoint(self.current_position, target):
            self.current_state = DroneState.FLYING
            self.current_waypoint_idx = 1

    def _handle_flying_state(self, dt: float) -> bool:
        """Handle FLYING state. Returns True if should continue, False if should return None."""
        if self.current_waypoint_idx >= len(self.waypoints):
            self.current_state = DroneState.RETURNING
            return False

        target = self.waypoints[self.current_waypoint_idx]
        self.current_position = self._move_towards_waypoint(self.current_position, target, dt)
        self.current_heading = self._calculate_heading(self.current_position, target)

        if self._is_at_waypoint(self.current_position, target):
            self.current_waypoint_idx += 1
        return True

    def _handle_returning_state(self, dt: float) -> None:
        """Handle RETURNING state."""
        target = WayPoint(self.start_point.easting, self.start_point.northing, self.target_altitude)
        self.current_position = self._move_towards_waypoint(self.current_position, target, dt)
        self.current_heading = self._calculate_heading(self.current_position, target)

        if self._is_at_waypoint(self.current_position, target):
            self.current_state = DroneState.LANDING

    def _handle_landing_state(self, dt: float) -> None:
        """Handle LANDING state."""
        target = self.start_point
        self.current_position = self._move_towards_waypoint(self.current_position, target, dt)

        if self._is_at_waypoint(self.current_position, target):
            self.current_state = DroneState.IDLE

    def _update_loop(self) -> None:
        """Main update loop for GPS position."""
        try:
            while self._running:
                current_time = time.time()
                dt = current_time - self._last_update
                self._last_update = current_time

                # Update position based on current state
                if self.current_state == DroneState.TAKEOFF:
                    self._handle_takeoff_state(dt)
                elif self.current_state == DroneState.FLYING:
                    if self.current_waypoint_idx >= len(self.waypoints):
                        self.current_state = DroneState.RETURNING
                    else:
                        self._handle_flying_state(dt)
                elif self.current_state == DroneState.RETURNING:
                    self._handle_returning_state(dt)
                elif self.current_state == DroneState.LANDING:
                    self._handle_landing_state(dt)

                # Sleep to maintain update rate
                time.sleep(1.0 / self.update_rate)
        except Exception:
            logger.exception("Error in GPS update loop")

    def start(self) -> None:
        """Start the GPS generator thread."""
        if self._update_thread is not None:
            return
        self._running = True
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()

    def stop(self) -> None:
        """Stop the GPS generator thread."""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=2.0)
            if self._update_thread.is_alive():
                logger.warning("GPS generator thread did not stop cleanly")
            self._update_thread = None

    def get_current_position(self) -> GPSData:
        """Get the current position with GPS noise."""
        # Add noise and generate GPS data
        noisy_easting, noisy_northing, noisy_altitude = self._add_gps_noise(
            self.current_position.easting,
            self.current_position.northing,
            self.current_position.altitude,
        )

        # Create GPS data packet
        self.packet_id += 1
        return GPSData(
            easting=noisy_easting,
            northing=noisy_northing,
            altitude=noisy_altitude,
            heading=self.current_heading,
            epsg_code=32611,  # EPSG code for UTM zone 11N
        )

    def start_flight(self) -> None:
        """Start the flight sequence."""
        if self.current_state == DroneState.IDLE:
            self.current_state = DroneState.TAKEOFF

    def return_to_home(self) -> None:
        """Command the drone to return to home."""
        if self.current_state in [DroneState.FLYING, DroneState.TAKEOFF]:
            self.current_state = DroneState.RETURNING


class SimulatorCore:
    """Controls the simulator instance and manages communication in a separate thread."""

    def __init__(self, radio_config: RadioConfig) -> None:
        """Initialize simulator with radio configuration."""
        self._comms = DroneComms(radio_config=radio_config, ack_timeout=1, max_retries=1)
        self._gps_generator = GpsDataGenerator()
        self._ping_finder: SimulatedPingFinder | None = None
        self._location_estimator: LocationEstimator | None = None
        self._running = True  # Set running to True initially
        self._pending_actions: dict[int, tuple[str, dict]] = {}
        self._rng = random.SystemRandom()
        self._gps_thread: threading.Thread | None = None

        # Register handlers and start communications
        self._register_handlers()
        self._start_drone_comms()

    def _register_handlers(self) -> None:
        """Register handlers for various drone commands."""
        self._comms.register_sync_request_handler(self._handle_sync_request)
        self._comms.register_start_request_handler(self._handle_start_request)
        self._comms.register_stop_request_handler(self._handle_stop_request)
        self._comms.register_config_request_handler(self._handle_config_request)

        self._comms.on_ack_success = self._handle_ack_success
        self._comms.on_ack_failure = self._handle_ack_failure

    def _start_drone_comms(self) -> None:
        """Start the drone communications and GPS data thread."""
        self._comms.start()
        self._gps_generator.start()  # Start GPS generator
        self._gps_thread = threading.Thread(target=self._gps_data_loop, daemon=True)
        self._gps_thread.start()

    def _gps_data_loop(self) -> None:
        """Main loop for sending GPS data."""
        logger.info("Starting GPS data loop")
        try:
            while self._running:
                # Get current position and send it
                gps_data = self._gps_generator.get_current_position()
                logger.info(
                    "Sending GPS data: easting=%.2f, northing=%.2f, altitude=%.2f, heading=%.2f",
                    gps_data.easting,
                    gps_data.northing,
                    gps_data.altitude,
                    gps_data.heading,
                )
                packet_id, _, _ = self._comms.send_gps_data(gps_data)
                logger.info("Sent GPS data with packet_id %d", packet_id)

                # Sleep for 1 second between updates
                time.sleep(1.0)
        except Exception:
            logger.exception("Error in GPS data loop")
        finally:
            logger.info("GPS data loop stopped")

    def _handle_ack_success(self, packet_id: int) -> None:
        """Handle successful acknowledgment."""
        logger.info("Received successful ACK for packet %d", packet_id)
        if packet_id not in self._pending_actions:
            logger.warning("No pending action found for packet %d", packet_id)
            return

        action_type, action_data = self._pending_actions.pop(packet_id)
        logger.info("Executing %s action for packet %d", action_type, packet_id)

        try:
            if action_type == "sync":
                self._execute_sync_action()
            elif action_type == "start":
                self._execute_start_action()
            elif action_type == "stop":
                self._execute_stop_action()
            elif action_type == "config":
                self._execute_config_action(action_data)
            logger.info("Successfully executed %s action", action_type)
        except Exception:
            msg = f"Failed to execute {action_type} action after acknowledgement"
            logger.exception(msg)
            self._comms.send_error(ErrorData())

    def _handle_ack_failure(self, packet_id: int) -> None:
        """Handle failed acknowledgment."""
        logger.warning("Received failed ACK for packet %d", packet_id)
        if packet_id in self._pending_actions:
            action_type, _ = self._pending_actions.pop(packet_id)
            logger.error("Failed to get acknowledgment for %s action (packet %d)", action_type, packet_id)
            self._comms.send_error(ErrorData())

    def _execute_sync_action(self) -> None:
        """Execute sync action after acknowledgment."""
        logger.info("Executing sync action")
        if self._ping_finder is not None:
            self._ping_finder.stop()
            self._ping_finder = None

    def _get_current_location(self, _: dt.datetime) -> tuple[float, float, float]:
        """Get current location for the location estimator."""
        pos = self._gps_generator.current_position
        logger.info("Location estimator getting position: (%.2f, %.2f, %.2f)", pos.easting, pos.northing, pos.altitude)
        return pos.easting, pos.northing, pos.altitude

    def _on_ping_detected(self, now: dt.datetime, amplitude: float, frequency: int) -> None:
        """Handle ping detection."""
        # Get current position
        pos = self._gps_generator.current_position
        logger.info(
            "Ping detected - Freq: %d Hz, Amplitude: %.2f dB, Position: (%.2f, %.2f, %.2f)",
            frequency,
            amplitude,
            pos.easting,
            pos.northing,
            pos.altitude,
        )

        # Send ping data
        ping_data = PingData(
            frequency=frequency,
            amplitude=amplitude,
            easting=pos.easting,
            northing=pos.northing,
            altitude=pos.altitude,
            epsg_code=32611,  # UTM zone 11N
        )
        self._comms.send_ping_data(ping_data)
        logger.debug("Sent ping data to GCS")

        # Add ping to location estimator and get estimate
        if self._location_estimator:
            self._location_estimator.add_ping(now, amplitude, frequency)
            try:
                estimate = self._location_estimator.do_estimate(frequency)
                if estimate is not None:
                    logger.info("Location estimate for %d Hz: (%.2f, %.2f)", frequency, estimate[0], estimate[1])
                    # Send location estimate
                    loc_est_data = LocEstData(
                        frequency=frequency,
                        easting=estimate[0],
                        northing=estimate[1],
                        epsg_code=32611,  # UTM zone 11N
                    )
                    self._comms.send_loc_est_data(loc_est_data)
                    logger.debug("Sent location estimate to GCS")
            except ValueError as e:
                logger.warning("Failed to estimate location: %s", str(e))
        else:
            logger.warning("Location estimator not initialized")

    def _execute_start_action(self) -> None:
        """Execute start action after acknowledgment."""
        if self._ping_finder is None:
            msg = "Cannot start ping finder: not configured"
            logger.error(msg)
            raise RuntimeError(msg)

        # Create location estimator if needed
        if self._location_estimator is None:
            self._location_estimator = LocationEstimator(self._get_current_location)

        # Register callback and start
        self._ping_finder.register_callback(self._on_ping_detected)
        self._ping_finder.start()
        self._gps_generator.start_flight()

    def _execute_stop_action(self) -> None:
        """Execute stop action after acknowledgment."""
        if self._ping_finder is None:
            msg = "Cannot stop ping finder: not configured"
            logger.error(msg)
            raise RuntimeError(msg)
        self._ping_finder.stop()
        self._gps_generator.return_to_home()
        self._location_estimator = None  # Reset location estimator

    def _execute_config_action(self, config_data: dict) -> None:
        """Execute config action after acknowledgment."""
        # Create new ping finder if needed
        if self._ping_finder is None:
            self._ping_finder = SimulatedPingFinder(self._gps_generator)

        # Add simulated transmitters based on target frequencies
        for freq in config_data["target_frequencies"]:
            # Place transmitters randomly in the search area
            x = self._rng.uniform(self._gps_generator.start_point.easting, self._gps_generator.end_point.easting)
            y = self._rng.uniform(self._gps_generator.start_point.northing, self._gps_generator.end_point.northing)
            z = 2.0  # Ground level
            self._ping_finder.add_transmitter(freq, (x, y, z))

    def _handle_sync_request(self, _: SyncRequestData) -> None:
        """Handle sync request from GCS."""
        logger.info("Received sync request from GCS")
        packet_id, _, _ = self._comms.send_sync_response(SyncResponseData(success=True))
        logger.info("Sent sync response with packet_id %d", packet_id)
        self._pending_actions[packet_id] = ("sync", {})

    def _handle_start_request(self, _: StartRequestData) -> None:
        """Handle start request from GCS."""
        logger.info("Received start request from GCS")
        success = self._ping_finder is not None
        packet_id, _, _ = self._comms.send_start_response(StartResponseData(success=success))
        logger.info("Sent start response with packet_id %d (success=%s)", packet_id, success)
        if success:
            self._pending_actions[packet_id] = ("start", {})
        else:
            logger.warning("Start request failed: ping finder not initialized")

    def _handle_stop_request(self, _: StopRequestData) -> None:
        """Handle stop request from GCS."""
        logger.info("Received stop request from GCS")
        success = self._ping_finder is not None
        packet_id, _, _ = self._comms.send_stop_response(StopResponseData(success=success))
        logger.info("Sent stop response with packet_id %d (success=%s)", packet_id, success)
        if success:
            self._pending_actions[packet_id] = ("stop", {})
        else:
            logger.warning("Stop request failed: ping finder not initialized")

    def _handle_config_request(self, data: ConfigRequestData) -> None:
        """Handle configuration request from GCS."""
        logger.info("Received config request from GCS")
        try:
            config_dict = {
                "gain": data.gain,
                "sampling_rate": data.sampling_rate,
                "center_frequency": data.center_frequency,
                "run_num": data.run_num,
                "enable_test_data": data.enable_test_data,
                "ping_width_ms": data.ping_width_ms,
                "ping_min_snr": data.ping_min_snr,
                "ping_max_len_mult": data.ping_max_len_mult,
                "ping_min_len_mult": data.ping_min_len_mult,
                "target_frequencies": list(data.target_frequencies),
            }
            logger.info("Config request data: %s", config_dict)

            packet_id, _, _ = self._comms.send_config_response(ConfigResponseData(success=True))
            logger.info("Sent config response with packet_id %d", packet_id)
            self._pending_actions[packet_id] = ("config", config_dict)

        except Exception:
            logger.exception("Failed to prepare config")
            self._comms.send_error(ErrorData())

    def start(self) -> None:
        """Start the simulator."""
        self._running = True
        if not self._gps_thread or not self._gps_thread.is_alive():
            self._gps_thread = threading.Thread(target=self._gps_data_loop, daemon=True)
            self._gps_thread.start()

    def stop(self) -> None:
        """Stop the simulator."""
        self._running = False
        if self._ping_finder:
            self._ping_finder.stop()
        self._gps_generator.stop()
        if self._gps_thread:
            self._gps_thread.join(timeout=2.0)
            if self._gps_thread.is_alive():
                logger.warning("GPS thread did not stop cleanly")


@dataclass
class Ping:
    """Ping dataclass."""

    x: float
    y: float
    z: float
    power: float
    freq: int
    time: dt.datetime

    def to_numpy(self) -> np.ndarray:
        """Converts the Ping to a numpy array.

        Returns:
            np.ndarray: Numpy array for processing
        """
        return np.array([self.x, self.y, self.z, self.power])


class LocationEstimator:
    """Location Estimator.

    All coordinate systems assumed have units in meters, using ENU order of axis
    """

    MIN_PINGS_FOR_ESTIMATE = 4

    def __init__(self, location_lookup: Callable[[dt.datetime], tuple[float, float, float]]) -> None:
        """Initialize location estimator with a location lookup function.

        Args:
            location_lookup: Function that returns (x, y, z) coordinates for a given timestamp
        """
        self.__loc_fn = location_lookup

        self.__pings: dict[int, list[Ping]] = {}

        self.__estimate: dict[int, np.ndarray] = {}

    def add_ping(self, now: dt.datetime, amplitude: float, frequency: int) -> None:
        """Adds a ping.

        Ping location is set via the location_lookup callback

        Args:
            now (dt.datetime): timestamp of ping
            amplitude (float): Amplitude of ping
            frequency (int): Ping frequency
        """
        x, y, z = self.__loc_fn(now)
        new_ping = Ping(x, y, z, amplitude, frequency, now)
        if frequency not in self.__pings:
            self.__pings[frequency] = [new_ping]
        else:
            self.__pings[frequency].append(new_ping)

    def do_estimate(
        self,
        frequency: int,
        *,
        xy_bounds: tuple[float, float, float, float] | None = None,
    ) -> tuple[float, float, float] | None:
        """Performs the estimate.

        Args:
            frequency (int): Frequency to estimate on
            xy_bounds (Tuple[float, float, float, float]): Optional XY bounds as
            [xmin xmax ymin ymax] to enforce on the estimate.  Defaults to UTM coordinate min/max.

        Raises:
            KeyError: Unknown frequency

        Returns:
            Optional[Tuple[float, float, float]]: If estimate is valid, the XYZ coordinates,
            otherwise, None
        """
        if frequency not in self.__pings:
            msg = "Unknown frequency"
            raise KeyError(msg)

        if len(self.__pings[frequency]) < self.MIN_PINGS_FOR_ESTIMATE:
            return None

        if not xy_bounds:
            xy_bounds = (167000, 833000, 0, 10000000)

        pings = np.array([ping.to_numpy() for ping in self.__pings[frequency]])

        # Get the actual transmitter position (last ping position)
        actual_x = pings[-1, 0]
        actual_y = pings[-1, 1]

        x_tx_0 = np.mean(pings[:, 0])
        y_tx_0 = np.mean(pings[:, 1])
        p_tx_0 = np.max(pings[:, 3])

        n_0 = 2

        params = self.__estimate[frequency] if frequency in self.__estimate else np.array([x_tx_0, y_tx_0, p_tx_0, n_0])
        res_x = least_squares(
            fun=self.__residuals,
            x0=params,
            bounds=([xy_bounds[0], xy_bounds[2], -np.inf, 2], [xy_bounds[1], xy_bounds[3], np.inf, 2.1]),
            args=(pings,),
        )

        if res_x.success:
            # Use the optimized parameters from res_x.x
            self.__estimate[frequency] = res_x.x
            retval = (res_x.x[0], res_x.x[1], 0)

            # Calculate distance between estimate and actual position
            distance = np.sqrt((res_x.x[0] - actual_x) ** 2 + (res_x.x[1] - actual_y) ** 2)
            logger.info(
                "Location estimate for %d Hz: (%.2f, %.2f), Distance from actual: %.2f m",
                frequency,
                res_x.x[0],
                res_x.x[1],
                distance,
            )
        else:
            retval = None

        return retval

    def get_frequencies(self) -> Iterable[int]:
        """Gets the current frequencies.

        Returns:
            Iterable[int]: Iterable of frequencies
        """
        return self.__pings.keys()

    def __residuals(self, params: np.ndarray, data: np.ndarray) -> np.ndarray:
        # Params is expected to be shape(4,)
        # Data is expected to be shape(n, 4)
        estimated_transmitter_x = params[0]
        estimated_transmitter_y = params[1]
        estimated_transmitter_location = np.array([estimated_transmitter_x, estimated_transmitter_y, 0])

        estimated_transmitter_power = params[2]
        estimated_model_order = params[3]

        received_power = data[:, 3]
        received_locations = data[:, 0:3]

        np.zeros(len(received_power))
        distances = np.linalg.norm(received_locations - estimated_transmitter_location, axis=1)
        return received_power - self.__distance_to_receive_power(
            distances,
            estimated_transmitter_power,
            estimated_model_order,
        )

    def __distance_to_receive_power(self, distance: np.ndarray, k: float, order: float) -> np.ndarray:
        return k - 10 * order * np.log10(distance)


class SimulatedPingFinder:
    """Simulates ping detection from radio transmitters."""

    SNR_THRESHOLD = -60  # dB
    MIN_DISTANCE = 1.0  # meters, avoid log(0)
    NOISE_STD = 2.0  # dB, standard deviation of noise
    PING_INTERVAL = 1.0  # seconds
    PING_JITTER = 0.1  # seconds
    MAX_DETECTION_RANGE = 500.0  # meters, maximum range where detection is possible
    BASE_DETECTION_PROB = 0.6  # base probability of detection at optimal range

    def __init__(self, gps_generator: GpsDataGenerator) -> None:
        """Initialize the simulated ping finder."""
        self._gps_generator = gps_generator
        self._callback: Callable[[dt.datetime, float, int], None] | None = None
        self._running: bool = False
        self._thread: threading.Thread | None = None
        self._rng = random.SystemRandom()

        # Simulated transmitter configurations
        self._transmitters: dict[int, tuple[float, float, float, float, float]] = {}  # freq -> (x, y, z, power, order)

        # Ping timing parameters
        self._next_ping_times: dict[int, float] = {}  # freq -> next ping time

    def _calculate_next_ping_time(self, current_time: float) -> float:
        """Calculate the next ping time with small jitter.

        Args:
            current_time: Current time in seconds

        Returns:
            float: Next ping time in seconds
        """
        jitter = self._rng.uniform(-self.PING_JITTER, self.PING_JITTER)
        return current_time + self.PING_INTERVAL + jitter

    def _calculate_detection_probability(self, distance: float) -> float:
        """Calculate probability of detection based on distance.

        Uses a sigmoid-like function that gives higher probability when closer
        to the transmitter and drops off as distance increases.

        Args:
            distance: Distance to transmitter in meters

        Returns:
            float: Probability of detection between 0 and 1
        """
        if distance > self.MAX_DETECTION_RANGE:
            return 0.0

        # Scale distance to be between 0 and 1
        scaled_dist = distance / self.MAX_DETECTION_RANGE
        # Use sigmoid-like function to calculate probability
        prob = self.BASE_DETECTION_PROB * (1 - scaled_dist**2)
        return max(0.0, min(1.0, prob))

    def _distance_to_receive_power(self, distance: float, k: float, order: float) -> float:
        """Calculate received power based on distance.

        Args:
            distance: Distance in meters
            k: Transmitter power in dB
            order: Path loss order

        Returns:
            float: Received power in dB
        """
        return k - 10 * order * np.log10(max(distance, self.MIN_DISTANCE))

    def register_callback(self, callback: Callable[[dt.datetime, float, int], None]) -> None:
        """Register callback for ping detections.

        Args:
            callback: Function to call when ping is detected with (timestamp, power, frequency)
        """
        self._callback = callback

    def add_transmitter(
        self,
        frequency: int,
        position: tuple[float, float, float],
        power: float = 100.0,
        order: float = 2.0,
    ) -> None:
        """Add a simulated transmitter.

        Args:
            frequency: Transmitter frequency in Hz
            position: (x, y, z) coordinates in UTM
            power: Transmitter power in dB
            order: Path loss order (typically 2-4)
        """
        self._transmitters[frequency] = (*position, power, order)
        # Initialize next ping time for this frequency with random offset
        self._next_ping_times[frequency] = time.time() + self._rng.uniform(0, self.PING_INTERVAL)

    def _should_ping(self, frequency: int) -> bool:
        """Determine if a ping should occur based on timing.

        Args:
            frequency: Transmitter frequency

        Returns:
            bool: True if should ping, False otherwise
        """
        current_time = time.time()
        next_ping_time = self._next_ping_times.get(frequency, current_time)

        if current_time >= next_ping_time:
            # Calculate next ping time
            self._next_ping_times[frequency] = self._calculate_next_ping_time(current_time)
            return True
        return False

    def _simulate_ping(self, frequency: int, drone_pos: WayPoint) -> tuple[float, bool]:
        """Simulate ping detection with realistic signal propagation.

        Args:
            frequency: Transmitter frequency
            drone_pos: Current drone position

        Returns:
            tuple[float, bool]: (received power in dB, whether ping was detected)
        """
        if frequency not in self._transmitters:
            return -float("inf"), False

        # Check if it's time for a ping
        if not self._should_ping(frequency):
            return -float("inf"), False

        tx_x, tx_y, tx_z, power, order = self._transmitters[frequency]

        # Calculate 3D distance to transmitter
        dx = tx_x - drone_pos.easting
        dy = tx_y - drone_pos.northing
        dz = tx_z - drone_pos.altitude
        distance = np.sqrt(dx * dx + dy * dy + dz * dz)

        # Calculate detection probability based on distance
        detection_prob = self._calculate_detection_probability(distance)

        # Random chance to miss the ping based on distance-based probability
        if self._rng.random() > detection_prob:
            return -float("inf"), False

        # Calculate received power with some noise
        received_power = self._distance_to_receive_power(distance, power, order)
        received_power += self._rng.gauss(0, self.NOISE_STD)

        # Determine if ping is detected (based on SNR threshold)
        is_detected = received_power > self.SNR_THRESHOLD

        return received_power, is_detected

    def _run(self) -> None:
        """Main simulation loop."""
        try:
            while self._running:
                now = dt.datetime.now(dt.UTC)
                pos = self._gps_generator.current_position

                # Simulate pings for each transmitter
                for freq in self._transmitters:
                    power, detected = self._simulate_ping(freq, pos)
                    if detected and self._callback:
                        self._callback(now, power, freq)

                # Sleep for a short time to check for pings
                time.sleep(0.1)  # Check more frequently for better timing accuracy
        except Exception:
            logger.exception("Error in ping simulation loop")

    def start(self) -> None:
        """Start the ping finder simulation."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the ping finder simulation."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.warning("Ping finder thread did not stop cleanly")
            self._thread = None
