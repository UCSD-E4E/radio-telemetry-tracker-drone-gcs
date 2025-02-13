import React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { GlobalAppState, PingFinderConfigState, RadioConfigState, FrequencyLayerVisibility } from './globalAppTypes';
import { GpsData, PingFinderConfig, POI, RadioConfig } from '../types/global';
import { MAP_SOURCES, MapSource } from '../utils/mapSources';
import { useInternetStatus } from '../hooks/useInternetStatus';
import { useConnectionQuality } from '../hooks/useConnectionQuality';
import { useGCSStateMachine } from '../hooks/useGCSStateMachine';
import { OFFLINE_MODE_KEY } from '../utils/mapSources';
import { TileInfo } from '../types/global';
import { GlobalAppContext } from './globalAppContextDef';
import type { Map as LeafletMap } from 'leaflet';
import { fetchBackend, FrequencyData } from '../utils/backend';
import { logToPython } from '../utils/logging';
import { GCSState } from './globalAppTypes'; 

const GlobalAppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    // Internet & Map Status
    const isOnline = useInternetStatus();
    const [isMapOfflinePreference, setIsMapOfflinePreference] = useState<boolean>(() => {
        const saved = window.localStorage.getItem(OFFLINE_MODE_KEY);
        return saved === 'true';
    });

    const isMapOffline = !isOnline || isMapOfflinePreference;

    const setIsMapOfflineUser = (val: boolean) => {
        setIsMapOfflinePreference(val);
        window.localStorage.setItem(OFFLINE_MODE_KEY, val.toString());
    };

    // Map Data
    const [currentMapSource, setCurrentMapSource] = useState<MapSource>(MAP_SOURCES[0]);
    const [tileInfo, setTileInfo] = useState<TileInfo | null>(null);
    const [pois, setPois] = useState<POI[]>([]);
    const [frequencyData, setFrequencyData] = useState<FrequencyData>({});
    const [frequencyVisibility, setFrequencyVisibility] = useState<FrequencyLayerVisibility[]>([]);
    const mapRef = useRef<LeafletMap | null>(null);

    // GPS Data
    const [gpsData, setGpsData] = useState<GpsData | null>(null);
    const [gpsDataUpdated, setGpsDataUpdated] = useState<boolean>(false);

    // Radio Configuration
    const [radioConfig, setRadioConfig] = useState<RadioConfigState>({
        interface_type: 'serial',
        serialPorts: [],
        selectedPort: '',
        baudRate: 57600,
        host: 'localhost',
        tcpPort: 50000,
        ackTimeout: 2000,
        maxRetries: 5,
    });

    // Ping Finder Configuration
    const [pingFinderConfig, setPingFinderConfig] = useState<PingFinderConfigState>({
        gain: 56.0,
        samplingRate: 2500000,
        centerFrequency: 173500000,
        enableTestData: false,
        pingWidthMs: 25,
        pingMinSnr: 25,
        pingMaxLenMult: 1.5,
        pingMinLenMult: 0.5,
        targetFrequencies: []
    });

    // Use our new hooks
    const { 
        gcsState, 
        connectionStatus, 
        message, 
        messageVisible, 
        messageType, 
        setupStateHandlers,
        setMessageVisible,
        setGcsState 
    } = useGCSStateMachine(window.backend);

    const { connectionQuality, pingTime, gpsFrequency } = useConnectionQuality(gpsData, connectionStatus === 1);

    // Fatal error
    const [fatalError, setFatalError] = useState<boolean>(false);

    // Simulator state
    const [isSimulatorRunning, setIsSimulatorRunning] = useState<boolean>(false);

    // Effect to setup state handlers when backend is available
    useEffect(() => {
        (async () => {
            const backend = await fetchBackend();
            setupStateHandlers();
            
            backend.gps_data_updated.connect((data: GpsData) => {
                setGpsData(data);
                setGpsDataUpdated(true);
            });

            backend.frequency_data_updated.connect((data: FrequencyData) => {
                setFrequencyData(data);
                setFrequencyVisibility(prev => {
                    const existingFreqs = new Set(prev.map(item => item.frequency));
                    const newFreqs = Object.entries(data)
                        .map(([freq]) => parseInt(freq))
                        .filter(freq => !existingFreqs.has(freq))
                        .map(freq => ({
                            frequency: freq,
                            visible_pings: true,
                            visible_location_estimate: true
                        }));
                    return [...prev, ...newFreqs];
                });
            });

            backend.tile_info_updated.connect((info: TileInfo) => {
                setTileInfo(info);
            });

            backend.pois_updated.connect((pois: POI[]) => {
                setPois(pois);
            });

            backend.fatal_error.connect(() => {
                setFatalError(true);
            });

            // Simulator signals
            backend.simulator_started.connect(() => {
                setIsSimulatorRunning(true);
            });

            backend.simulator_stopped.connect(() => {
                setIsSimulatorRunning(false);
            });

        })();
    }, [setupStateHandlers]);

    // Callback functions
    const deleteFrequencyLayer = useCallback(async (frequency: number) => {
        if (!window.backend) return false;
        try {
            const success = await window.backend.clear_frequency_data(frequency);
            if (!success) return false;
            setFrequencyVisibility(prev => prev.filter(item => item.frequency !== frequency));
            return true;
        } catch (err) {
            console.error('Error deleting frequency layer:', err);
            return false;
        }
    }, []);

    const deleteAllFrequencyLayers = useCallback(async () => {
        if (!window.backend) return false;
        try {
            const success = await window.backend.clear_all_frequency_data();
            if (!success) return false;
            setFrequencyVisibility([]);
            return true;
        } catch (err) {
            console.error('Error deleting all frequency layers:', err);
            return false;
        }
    }, []);

    const loadPOIs = useCallback(async () => {
        if (!window.backend) return;
        try {
            const data = await window.backend.get_pois();
            setPois(data);
        } catch (err) {
            console.error('Error loading POIs:', err);
        }
    }, []);

    const addPOI = useCallback(async (name: string, coords: [number, number]) => {
        if (!window.backend) return false;
        try {
            return await window.backend.add_poi(name, coords);
        } catch (err) {
            const errorMsg = 'Error adding POI: ' + err;
            console.error(errorMsg);
            logToPython(errorMsg);
            return false;
        }
    }, []);

    const removePOI = useCallback(async (name: string) => {
        if (!window.backend) return false;
        try {
            return await window.backend.remove_poi(name);
        } catch (err) {
            const errorMsg = 'Error removing POI: ' + err;
            console.error(errorMsg);
            logToPython(errorMsg);
            return false;
        }
    }, []);

    const clearTileCache = useCallback(async () => {
        if (!window.backend) return false;
        try {
            return await window.backend.clear_tile_cache();
        } catch (err) {
            const errorMsg = 'Error clearing tile cache: ' + err;
            console.error(errorMsg);
            logToPython(errorMsg);
            return false;
        }
    }, []);

    const loadSerialPorts = useCallback(async () => {
        if (!window.backend) return;
        try {
            const ports = await window.backend.get_serial_ports();
            setRadioConfig(prev => ({ ...prev, serialPorts: ports }));
        } catch (err) {
            const errorMsg = 'Error loading serial ports: ' + err;
            console.error(errorMsg);
            logToPython(errorMsg);
        }
    }, []);

    const sendRadioConfig = useCallback(async () => {
        setMessageVisible(false);
        if (!window.backend) return false;
        const radioConfigSend = {
            interface_type: radioConfig.interface_type,
            port: radioConfig.selectedPort,
            baudrate: radioConfig.baudRate,
            host: radioConfig.host,
            tcp_port: radioConfig.tcpPort,
            ack_timeout: radioConfig.ackTimeout / 1000,
            max_retries: radioConfig.maxRetries,
        } as RadioConfig;

        if (radioConfig.interface_type === 'serial') {
            if (!radioConfig.selectedPort) return false;
        } else {
            if (!radioConfig.host || !radioConfig.tcpPort) return false;
        }

        try {
            setGcsState(GCSState.RADIO_CONFIG_WAITING);
            return await window.backend.initialize_comms(radioConfigSend);
        } catch (e) {
            console.error('Failed to sendRadioConfig', e);
            setGcsState(GCSState.RADIO_CONFIG_INPUT);
            return false;
        }
    }, [radioConfig, setMessageVisible, setGcsState]);

    const cancelRadioConfig = useCallback(async () => {
        setMessageVisible(false);
        if (!window.backend) return false;
        try {
            setGcsState(GCSState.RADIO_CONFIG_INPUT);
            await window.backend.cancel_connection();
            return true;
        } catch (e) {
            console.error('Failed to cancelRadioConfig', e);
            return false;
        }
    }, [setMessageVisible, setGcsState]);

    const sendPingFinderConfig = useCallback(async () => {
        setMessageVisible(false);
        if (!window.backend) return false;

        const pingFinderConfigSend = {
            gain: pingFinderConfig.gain,
            sampling_rate: pingFinderConfig.samplingRate,
            center_frequency: pingFinderConfig.centerFrequency,
            enable_test_data: pingFinderConfig.enableTestData,
            ping_width_ms: pingFinderConfig.pingWidthMs,
            ping_min_snr: pingFinderConfig.pingMinSnr,
            ping_max_len_mult: pingFinderConfig.pingMaxLenMult,
            ping_min_len_mult: pingFinderConfig.pingMinLenMult,
            target_frequencies: pingFinderConfig.targetFrequencies,
        } as PingFinderConfig;

        if (pingFinderConfig.targetFrequencies.length === 0) return false;

        try {
            setGcsState(GCSState.PING_FINDER_CONFIG_WAITING);
            return await window.backend.send_config_request(pingFinderConfigSend);
        } catch (e) {
            console.error('Failed to sendPingFinderConfig', e);
            setGcsState(GCSState.PING_FINDER_CONFIG_INPUT);
            return false;
        }
    }, [pingFinderConfig, setMessageVisible, setGcsState]);

    const cancelPingFinderConfig = useCallback(async () => {
        setMessageVisible(false);
        if (!window.backend) return false;
        try {
            setGcsState(GCSState.PING_FINDER_CONFIG_INPUT);
            return await window.backend.cancel_config_request();
        } catch (e) {
            console.error('Failed to cancelPingFinderConfig', e);
            return false;
        }
    }, [setMessageVisible, setGcsState]);

    const start = useCallback(async () => {
        setMessageVisible(false);
        if (!window.backend) return false;
        try {
            setGcsState(GCSState.START_WAITING);
            return await window.backend.send_start_request();
        } catch (e) {
            console.error('Failed to start', e);
            setGcsState(GCSState.START_INPUT);
            return false;
        }
    }, [setMessageVisible, setGcsState]);

    const cancelStart = useCallback(async () => {
        setMessageVisible(false);
        if (!window.backend) return false;
        try {
            setGcsState(GCSState.START_INPUT);
            return await window.backend.cancel_start_request();
        } catch (e) {
            console.error('Failed to cancelStart', e);
            return false;
        }
    }, [setMessageVisible, setGcsState]);

    const stop = useCallback(async () => {
        setMessageVisible(false);
        if (!window.backend) return false;
        try {
            setGcsState(GCSState.STOP_WAITING);
            return await window.backend.send_stop_request();
        } catch (e) {
            console.error('Failed to stop', e);
            setGcsState(GCSState.STOP_INPUT);
            return false;
        }
    }, [setMessageVisible, setGcsState]);

    const cancelStop = useCallback(async () => {
        setMessageVisible(false);
        if (!window.backend) return false;
        try {
            setGcsState(GCSState.STOP_INPUT);
            return await window.backend.cancel_stop_request();
        } catch (e) {
            console.error('Failed to cancelStop', e);
            return false;
        }
    }, [setMessageVisible, setGcsState]);

    const disconnect = useCallback(async () => {
        setMessageVisible(false);
        if (!window.backend) return false;
        try {
            await window.backend.disconnect();
            return true;
        } catch (e) {
            console.error('Failed to disconnect', e);
            return false;
        }
    }, [setMessageVisible]);

    // Simulator functions
    const initSimulator = useCallback(async (config: RadioConfig) => {
        if (!window.backend) return false;
        try {
            return await window.backend.init_simulator(config);
        } catch (e) {
            console.error('Failed to initialize simulator', e);
            return false;
        }
    }, []);

    const cleanupSimulator = useCallback(async () => {
        if (!window.backend) return false;
        try {
            return await window.backend.cleanup_simulator();
        } catch (e) {
            console.error('Failed to cleanup simulator', e);
            return false;
        }
    }, []);

    const value: GlobalAppState = {
        // Simulator
        initSimulator,
        cleanupSimulator,
        isSimulatorRunning,

        // Connection Quality State
        connectionQuality,
        pingTime,
        gpsFrequency,

        // GCS State Machine
        gcsState,
        connectionStatus,
        message,
        messageVisible,
        messageType,
        setupStateHandlers,
        setMessageVisible,
        setGcsState,

        // Map Data
        isMapOffline,
        setIsMapOfflineUser,
        currentMapSource,
        setCurrentMapSource,
        mapSources: MAP_SOURCES,
        tileInfo,
        pois,
        frequencyData,
        deleteFrequencyLayer,
        deleteAllFrequencyLayers,
        frequencyVisibility,
        setFrequencyVisibility,
        mapRef,
        loadPOIs,
        addPOI,
        removePOI,
        clearTileCache,

        // GPS Data
        gpsData,
        gpsDataUpdated,
        setGpsDataUpdated,

        // Radio Configuration
        radioConfig,
        setRadioConfig,
        loadSerialPorts,
        sendRadioConfig,
        cancelRadioConfig,

        // Ping Finder Configuration
        pingFinderConfig,
        setPingFinderConfig,
        sendPingFinderConfig,
        cancelPingFinderConfig,

        // Control Operations
        start,
        cancelStart,
        stop,
        cancelStop,
        disconnect,

        fatalError,
    };

    return (
        <GlobalAppContext.Provider value={value}>
            {children}
        </GlobalAppContext.Provider>
    );
}

export default GlobalAppProvider;

