"""Wraps user-provided DroneComms, handles start/stop, sending requests."""

from __future__ import annotations

from typing import Callable

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


class DroneCommsService:
    """Manages DroneComms lifecycle and sending requests (sync, config, start, stop)."""

    def __init__(
        self,
        radio_config: RadioConfig,
        ack_timeout: float,
        max_retries: int,
        on_ack_success: Callable[[int], None] | None = None,
        on_ack_timeout: Callable[[int], None] | None = None,
    ) -> None:
        """Initialize drone communications service with radio config and acknowledgment settings.

        Args:
            radio_config: Radio configuration parameters
            ack_timeout: Time to wait for acknowledgment
            max_retries: Maximum retry attempts for failed transmissions
            on_ack_success: Callback when acknowledgment received
            on_ack_timeout: Callback when acknowledgment times out
        """
        self.radio_config = radio_config
        self.ack_timeout = ack_timeout
        self.max_retries = max_retries
        self._comms = DroneComms(
            radio_config=radio_config,
            ack_timeout=ack_timeout,
            max_retries=max_retries,
        )
        # Set callbacks after initialization
        if on_ack_success:
            self._comms.on_ack_success = on_ack_success
        if on_ack_timeout:
            self._comms.on_ack_timeout = on_ack_timeout
        self._started = False

    def start(self) -> None:
        """Start the drone communications service."""
        if not self._started:
            self._comms.start()
            self._started = True

    def stop(self) -> None:
        """Stop the drone communications service."""
        if self._started:
            self._comms.stop()
            self._started = False

    def is_started(self) -> bool:
        """Check if the service is started.

        Returns:
            bool: True if started, False otherwise
        """
        return self._started

    # Registration for packet handlers
    def register_sync_response_handler(
        self,
        callback: Callable[[SyncResponseData], None],
        *,
        once: bool = True,
    ) -> None:
        """Register a callback to handle sync response packets from the drone."""
        self._comms.register_sync_response_handler(callback, once=once)

    def unregister_sync_response_handler(self, callback: Callable[[SyncResponseData], None]) -> None:
        """Unregister a callback to handle sync response packets from the drone."""
        self._comms.unregister_sync_response_handler(callback)

    def register_config_response_handler(
        self,
        callback: Callable[[ConfigResponseData], None],
        *,
        once: bool = True,
    ) -> None:
        """Register a callback to handle config response packets from the drone."""
        self._comms.register_config_response_handler(callback, once=once)

    def unregister_config_response_handler(self, callback: Callable[[ConfigResponseData], None]) -> None:
        """Unregister a callback to handle config response packets from the drone."""
        self._comms.unregister_config_response_handler(callback)

    def register_start_response_handler(
        self,
        callback: Callable[[StartResponseData], None],
        *,
        once: bool = True,
    ) -> None:
        """Register a callback to handle start response packets from the drone."""
        self._comms.register_start_response_handler(callback, once=once)

    def unregister_start_response_handler(self, callback: Callable[[StartResponseData], None]) -> None:
        """Unregister a callback to handle start response packets from the drone."""
        self._comms.unregister_start_response_handler(callback)

    def register_stop_response_handler(
        self,
        callback: Callable[[StopResponseData], None],
        *,
        once: bool = True,
    ) -> None:
        """Register a callback to handle stop response packets from the drone."""
        self._comms.register_stop_response_handler(callback, once=once)

    def unregister_stop_response_handler(self, callback: Callable[[StopResponseData], None]) -> None:
        """Unregister a callback to handle stop response packets from the drone."""
        self._comms.unregister_stop_response_handler(callback)

    def register_gps_handler(
        self,
        callback: Callable[[GPSData], None],
        *,
        once: bool = True,
    ) -> None:
        """Register a callback to handle GPS data packets from the drone."""
        self._comms.register_gps_handler(callback, once=once)

    def unregister_gps_handler(self, callback: Callable[[GPSData], None]) -> None:
        """Unregister a callback to handle GPS data packets from the drone."""
        self._comms.unregister_gps_handler(callback)

    def register_ping_handler(
        self,
        callback: Callable[[PingData], None],
        *,
        once: bool = True,
    ) -> None:
        """Register a callback to handle ping packets from the drone."""
        self._comms.register_ping_handler(callback, once=once)

    def unregister_ping_handler(self, callback: Callable[[PingData], None]) -> None:
        """Unregister a callback to handle ping packets from the drone."""
        self._comms.unregister_ping_handler(callback)

    def register_loc_est_handler(
        self,
        callback: Callable[[LocEstData], None],
        *,
        once: bool = True,
    ) -> None:
        """Register a callback to handle location estimation data packets from the drone."""
        self._comms.register_loc_est_handler(callback, once=once)

    def unregister_loc_est_handler(self, callback: Callable[[LocEstData], None]) -> None:
        """Unregister a callback to handle location estimation data packets from the drone."""
        self._comms.unregister_loc_est_handler(callback)

    def register_error_handler(
        self,
        callback: Callable[[ErrorData], None],
        *,
        once: bool = True,
    ) -> None:
        """Register a callback to handle error data packets from the drone."""
        self._comms.register_error_handler(callback, once=once)

    def unregister_error_handler(self, callback: Callable[[ErrorData], None]) -> None:
        """Unregister a callback to handle error data packets from the drone."""
        self._comms.unregister_error_handler(callback)

    # Sending requests
    def send_sync_request(self) -> int:
        """Send a sync request to the drone and return the packet ID."""
        data = SyncRequestData(
            ack_timeout=self.ack_timeout,
            max_retries=self.max_retries,
        )
        packet_id, need_ack, ts = self._comms.send_sync_request(data)
        return packet_id

    def send_config_request(self, cfg: ConfigRequestData) -> int:
        """Send a configuration request to the drone and return the packet ID."""
        packet_id, need_ack, ts = self._comms.send_config_request(cfg)
        return packet_id

    def send_start_request(self) -> int:
        """Send a start request to the drone and return the packet ID."""
        req = StartRequestData()
        packet_id, need_ack, ts = self._comms.send_start_request(req)
        return packet_id

    def send_stop_request(self) -> int:
        """Send a stop request to the drone and return the packet ID."""
        req = StopRequestData()
        packet_id, need_ack, ts = self._comms.send_stop_request(req)
        return packet_id
