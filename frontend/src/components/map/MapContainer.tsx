import React, { useContext, useEffect, useState, useRef } from 'react';
import { MapContainer as LeafletMap, useMap, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { Map } from 'leaflet';
import type { TileEvent } from 'leaflet';
import NavigationControls from './NavigationControls';
import DataLayers from './DataLayers';
import { GlobalAppContext } from '../../context/globalAppContextDef';
import { logToPython } from '../../utils/logging';
import MapOverlayControls from './MapOverlayControls';
import MapDrawingControls from './MapDrawingControls';
import MapDrawingLayer from './MapDrawingLayer';
import { MapShapesProvider } from '../../context/MapShapesContext';


const DEFAULT_CENTER: [number, number] = [32.8801, -117.2340];
const DEFAULT_ZOOM = 13;
const BATCH_DELAY = 50; // ms to wait before processing batch

// A custom tile layer hooking into the backend
const CustomTileLayer: React.FC<{
    source: string;
    isOffline: boolean;
    attribution: string;
    maxZoom: number;
    minZoom: number;
    onOfflineMiss: () => void;
}> = ({ source, isOffline, attribution, maxZoom, minZoom, onOfflineMiss }) => {
    const [isBackendReady, setIsBackendReady] = useState(false);
    const pendingRequests = useRef<Record<string, { tile: HTMLImageElement; controller: AbortController }>>({});
    const batchTimeoutRef = useRef<number | null>(null);

    useEffect(() => {
        const initBackend = async () => {
            await new Promise<void>((resolve) => {
                if (window.backendLoaded) resolve();
                else window.addEventListener('backendLoaded', () => resolve(), { once: true });
            });
            setIsBackendReady(true);
        };
        initBackend();

        // Cleanup function
        return () => {
            if (batchTimeoutRef.current !== null) {
                window.clearTimeout(batchTimeoutRef.current);
            }
            // Cancel all pending requests
            Object.values(pendingRequests.current).forEach(({ controller }) => controller.abort());
            pendingRequests.current = {};
        };
    }, []);

    const processTileBatch = async () => {
        if (!isBackendReady) return;
        
        const requests = { ...pendingRequests.current };
        pendingRequests.current = {};
        batchTimeoutRef.current = null;

        await Promise.all(
            Object.entries(requests).map(async ([key, { tile, controller }]) => {
                if (controller.signal.aborted) return;

                const [z, x, y] = key.split(',').map(Number);
                try {
                    const tileData = await window.backend.get_tile(z, x, y, source, {
                        offline: isOffline,
                    });
                    if (controller.signal.aborted) return;
                    
                    if (tileData) {
                        tile.src = `data:image/png;base64,${tileData}`;
                    } else if (isOffline) {
                        onOfflineMiss();
                    }
                } catch (err) {
                    if (!controller.signal.aborted) {
                        const errorMsg = 'Error loading tile: ' + err;
                        console.error(errorMsg);
                        logToPython(errorMsg);
                    }
                }
            })
        );
    };

    const eventHandlers = {
        tileloadstart: (evt: TileEvent) => {
            if (!isBackendReady) return;

            const tile = evt.tile as HTMLImageElement;
            const coords = evt.coords;
            const key = `${coords.z},${coords.x},${coords.y}`;

            // Cancel previous request for this tile if it exists
            const existing = pendingRequests.current[key];
            if (existing) {
                existing.controller.abort();
            }

            // Create new request
            const controller = new AbortController();
            pendingRequests.current[key] = { tile, controller };

            // Schedule batch processing
            if (batchTimeoutRef.current !== null) {
                window.clearTimeout(batchTimeoutRef.current);
            }
            batchTimeoutRef.current = window.setTimeout(processTileBatch, BATCH_DELAY);
        },
    };

    return (
        <TileLayer
            url="about:blank"
            tileSize={256}
            attribution={attribution}
            maxZoom={maxZoom}
            minZoom={minZoom}
            eventHandlers={eventHandlers}
        />
    );
};

const FixMapSize: React.FC = () => {
    const map = useMap();
    useEffect(() => {
        map.invalidateSize();
    }, [map]);
    return null;
};

const MapContainer: React.FC = () => {
    const context = useContext(GlobalAppContext);
    if (!context) throw new Error('MapContainer must be in GlobalAppProvider');

    const { currentMapSource, isMapOffline, mapRef } = context;
    const [tileError, setTileError] = useState<string | null>(null);

    useEffect(() => {
        setTileError(null);
    }, [currentMapSource.id, isMapOffline]);

    const onMapCreated = (map: Map) => {
        mapRef.current = map;
    };

    return (
        <MapShapesProvider>
            <div className="h-full w-full relative">
                <LeafletMap
                    center={DEFAULT_CENTER}
                    zoom={DEFAULT_ZOOM}
                    className="h-full w-full relative z-[1000]"
                    zoomControl={false}
                    attributionControl={false}
                    ref={onMapCreated}
                >
                    <CustomTileLayer
                        source={currentMapSource.id}
                        isOffline={isMapOffline}
                        attribution={currentMapSource.attribution}
                        maxZoom={currentMapSource.maxZoom}
                        minZoom={currentMapSource.minZoom}
                        onOfflineMiss={() =>
                            setTileError('Some tiles are not available offline. Please cache them in online mode first.')
                        }
                    />
                    <FixMapSize />
                    <NavigationControls />
                    <DataLayers />
                    <MapDrawingLayer />
                </LeafletMap>
                {tileError && (
                    <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-[1001]">
                        {tileError}
                    </div>
                )}
                <MapOverlayControls />
                <MapDrawingControls />
            </div>
        </MapShapesProvider>
    );
};

export default MapContainer;
