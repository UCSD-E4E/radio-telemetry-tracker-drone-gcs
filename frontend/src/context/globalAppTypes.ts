import type { Map } from 'leaflet';
import type { RefObject } from 'react';
import type { GpsData, POI, TileInfo, RadioConfig } from '../types/global';
import type { MapSource } from '../utils/mapSources';
import { FrequencyData, TrackingSession } from '../utils/backend';
import type { ConnectionQualityState } from '../hooks/useConnectionQuality';
import type { GCSStateMachineState } from '../hooks/useGCSStateMachine';

export enum GCSState {
    RADIO_CONFIG_INPUT = 'RADIO_CONFIG_INPUT',
    RADIO_CONFIG_WAITING = 'RADIO_CONFIG_WAITING',
    RADIO_CONFIG_TIMEOUT = 'RADIO_CONFIG_TIMEOUT',
    PING_FINDER_CONFIG_INPUT = 'PING_FINDER_CONFIG_INPUT',
    PING_FINDER_CONFIG_WAITING = 'PING_FINDER_CONFIG_WAITING',
    PING_FINDER_CONFIG_TIMEOUT = 'PING_FINDER_CONFIG_TIMEOUT',
    START_INPUT = 'START_INPUT',
    START_WAITING = 'START_WAITING',
    START_TIMEOUT = 'START_TIMEOUT',
    STOP_INPUT = 'STOP_INPUT',
    STOP_WAITING = 'STOP_WAITING',
    STOP_TIMEOUT = 'STOP_TIMEOUT'
}

export interface RadioConfigState {
    interface_type: 'serial' | 'simulated';
    serialPorts: string[];
    selectedPort: string;
    baudRate: number;
    host: string;
    tcpPort: number;
    ackTimeout: number;
    maxRetries: number;
}

export interface PingFinderConfigState {
    gain: number;
    samplingRate: number;
    centerFrequency: number;
    enableTestData: boolean;
    pingWidthMs: number;
    pingMinSnr: number;
    pingMaxLenMult: number;
    pingMinLenMult: number;
    targetFrequencies: number[];
}

export interface FrequencyLayerVisibility {
    frequency: number;
    visible_pings: boolean;
    visible_location_estimate: boolean;
}

export interface GlobalAppState extends ConnectionQualityState, GCSStateMachineState {
    // Simulator
    initSimulator: (config: RadioConfig) => Promise<boolean>;
    cleanupSimulator: () => Promise<boolean>;
    isSimulatorRunning: boolean;

    // Map Data
    isMapOffline: boolean;
    setIsMapOfflineUser: (val: boolean) => void;
    currentMapSource: MapSource;
    setCurrentMapSource: (src: MapSource) => void;
    mapSources: MapSource[];
    tileInfo: TileInfo | null;
    pois: POI[];
    frequencyData: FrequencyData; 
    frequencyData1: FrequencyData; //tracking session loaded data 

    deleteFrequencyLayer: (frequency: number) => void;
    deleteAllFrequencyLayers: () => void;
    frequencyVisibility: FrequencyLayerVisibility[];
    setFrequencyVisibility: (visibility: FrequencyLayerVisibility[]) => void;
    frequencyVisibility1: FrequencyLayerVisibility[]; //tracking session loaded data visibility
    setFrequencyVisibility1: (visibility: FrequencyLayerVisibility[]) => void; //tracking session loaded data visibility
    mapRef: RefObject<Map | null>;
    loadPOIs: () => Promise<void>;
    addPOI: (name: string, coords: [number, number]) => Promise<boolean>;
    removePOI: (name: string) => Promise<boolean>;
    clearTileCache: () => Promise<boolean>;

    //Tracking Session 
    get_frequencies_by_session: (sessionName: string) => Promise<TrackingSession>;
    save_frequencies_to_session: (sessionName: string, sessionDate: string, frequencies: TrackingSession) => Promise<number>;
    get_all_tracking_session_names: () => Promise<string[]> ; 
    loadedSessionNames: string[]; 
    setLoadedSessionNames: (sessionName: string[]) => void;
    removeTrackingSessionFromMap: (sessionName: string) => void; 


    // GPS data
    gpsData: GpsData | null;
    gpsDataUpdated: boolean;
    setGpsDataUpdated: (updated: boolean) => void;

    // Radio configuration
    radioConfig: RadioConfigState;
    setRadioConfig: (config: RadioConfigState) => void;
    loadSerialPorts: () => Promise<void>;
    sendRadioConfig: () => Promise<boolean>;
    cancelRadioConfig: () => void;

    // Ping finder configuration
    pingFinderConfig: PingFinderConfigState;
    setPingFinderConfig: (config: PingFinderConfigState) => void;
    sendPingFinderConfig: () => Promise<boolean>;
    cancelPingFinderConfig: () => void;

    // Start
    start: () => Promise<boolean>;
    cancelStart: () => void;

    // Stop
    stop: () => Promise<boolean>;
    cancelStop: () => void;

    // Disconnect
    disconnect: () => Promise<boolean>;

    // GCS State Machine
    gcsState: GCSState;
    connectionStatus: 1 | 0;
    message: string;
    messageVisible: boolean;
    messageType: 'error' | 'success';
    setupStateHandlers: () => void;
    setMessageVisible: (visible: boolean) => void;
    setGcsState: (state: GCSState) => void;

    // Fatal Error State
    fatalError: boolean;
}
