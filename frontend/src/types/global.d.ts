import type { DroneBackend } from '../utils/backend';

declare global {
    interface Window {
        backend: DroneBackend;
        backendLoaded: boolean;
    }
}

export type TimeoutRef = ReturnType<typeof setTimeout>;

export interface GpsData {
    lat: number;
    long: number;
    altitude: number;
    heading: number;
    timestamp: number;
    packet_id: number;
}

export interface PingData {
    frequency: number;
    amplitude: number;
    lat: number;
    long: number;
    timestamp: number;
    packet_id: number;
}

export interface LocEstData {
    frequency: number;
    lat: number;
    long: number;
    timestamp: number;
    packet_id: number;
}

export interface POI {
    name: string;
    coords: [number, number];
}

export interface TileInfo {
    total_tiles: number;
    total_size_mb: number;
}

export interface RadioConfig {
    interface_type: 'serial' | 'simulated';
    port: string;
    baudrate: number;
    host: string;
    tcp_port: number;
    ack_timeout: number;
    max_retries: number;
}

export interface PingFinderConfig {
    gain: number;
    sampling_rate: number;
    center_frequency: number;
    enable_test_data: boolean;
    ping_width_ms: number;
    ping_min_snr: number;
    ping_max_len_mult: number;
    ping_min_len_mult: number;
    target_frequencies: number[];
}

export interface TileOptions {
    offline: boolean;
}

export interface FrequencyRecord {
    frequency: number;
    data_type: "ping" | "location_estimate";
    latitude: number;
    longitude: number;
    amplitude: number | null;
    timestamp: number;
}

export type TrackingSession = FrequencyRecord[];

export { };
