"""Data models for internal representation of drone telemetry data."""

from dataclasses import dataclass


@dataclass
class GpsData:
    """GPS position data from the drone including latitude, longitude, altitude, and heading."""
    lat: float
    long: float
    altitude: float
    heading: float
    timestamp: int
    packet_id: int


@dataclass
class PingData:
    """Radio ping detection data including frequency, amplitude, and location."""
    frequency: int
    amplitude: float
    lat: float
    long: float
    timestamp: int
    packet_id: int


@dataclass
class LocEstData:
    """Location estimate data for a specific frequency based on ping detections."""
    frequency: int
    lat: float
    long: float
    timestamp: int
    packet_id: int
