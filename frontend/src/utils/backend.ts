import type {
    GpsData,
    PingData,
    LocEstData,
    POI,
    TileInfo,
    RadioConfig,
    PingFinderConfig,
    TileOptions
} from '../types/global';

export interface Signal<T> {
    connect: (callback: (data: T) => void) => void;
    disconnect: (callback?: (data: T) => void) => void;
}

export interface FrequencyData {
    [frequency: number]: {
        pings: PingData[];
        locationEstimate: LocEstData | null;
    }
}

export interface TrackingSession {
    id: number;
    name: string;
    description?: string; 
    createdAt: string; 
    updatedAt: string; 
}


export interface DroneBackend {
    // Connection
    get_serial_ports(): Promise<string[]>;
    initialize_comms(config: RadioConfig): Promise<boolean>;
    cancel_connection(): void;
    disconnect(): void;

    // Simulator
    init_simulator(config: RadioConfig): Promise<boolean>;
    cleanup_simulator(): Promise<boolean>;
    simulator_started: Signal<void>;
    simulator_stopped: Signal<void>;

    // Data signals
    gps_data_updated: Signal<GpsData>;
    frequency_data_updated: Signal<FrequencyData>;

    // Tracking Session Signal 
    tracking_session_updated: Signal<TrackingSession[]>;

    // Fatal error signal
    fatal_error: Signal<void>;

    // Operation signals
    sync_success: Signal<string>;
    sync_failure: Signal<string>;
    sync_timeout: Signal<void>;

    config_success: Signal<string>;
    config_failure: Signal<string>;
    config_timeout: Signal<void>;

    start_success: Signal<string>;
    start_failure: Signal<string>;
    start_timeout: Signal<void>;

    stop_success: Signal<string>;
    stop_failure: Signal<string>;
    stop_timeout: Signal<void>;

    disconnect_success: Signal<string>;
    disconnect_failure: Signal<string>;

    // Tiles
    get_tile(z: number, x: number, y: number, source: string, options: TileOptions): Promise<string>;
    get_tile_info(): Promise<TileInfo>;
    clear_tile_cache(): Promise<boolean>;
    tile_info_updated: Signal<TileInfo>;

    // POIs
    get_pois(): Promise<POI[]>;
    add_poi(name: string, coords: [number, number]): Promise<boolean>;
    remove_poi(name: string): Promise<boolean>;
    rename_poi(oldName: string, newName: string): Promise<boolean>;
    pois_updated: Signal<POI[]>;

    // Tracking Session's 
    add_tracking_session(name: string, description: string): Promise<boolean>;
    remove_tracking_session(id: number): Promise<boolean>;
    get_tracking_sessions(): Promise<TrackingSession[]>;
    add_frequency(frequency: number, signal_strength: number, tracking_session_id: number): Promise<boolean>;
    remove_frequency(id: number): Promise<boolean>;
    get_frequencies_by_session(id: number): Promise<FrequencyData>;

    // Config and Control
    send_config_request(config: PingFinderConfig): Promise<boolean>;
    cancel_config_request(): Promise<boolean>;
    send_start_request(): Promise<boolean>;
    cancel_start_request(): Promise<boolean>;
    send_stop_request(): Promise<boolean>;
    cancel_stop_request(): Promise<boolean>;

    // Data Management
    clear_frequency_data(freq: number): Promise<boolean>;
    clear_all_frequency_data(): Promise<boolean>;

    // Logging
    log_message(message: string): void;
}

declare global {
    interface Window {
        backend: DroneBackend;
        backendLoaded: boolean;
    }
}

export async function fetchBackend(): Promise<DroneBackend> {
    return new Promise((resolve) => {
        if (window.backend) {
            resolve(window.backend);
        } else {
            window.addEventListener('backendLoaded', () => {
                resolve(window.backend);
            });
        }
    });
}
