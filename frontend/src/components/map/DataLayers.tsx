import React, { useEffect, useCallback, useState, useRef, useMemo, useContext } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { formatDistanceToNow, isValid } from 'date-fns';
import { logToPython } from '../../utils/logging';
import type { GpsData, TimeoutRef, PingData, LocEstData } from '../../types/global';
import { GlobalAppContext } from '../../context/globalAppContextDef';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

// Helper functions for visualization
const normalize = (value: number, min: number, max: number) => {
    if (min === max) return 0.5;
    return (value - min) / (max - min);
};

// Generate a distinct color based on frequency
const getFrequencyColor = (frequency: number): string => {
    // Use golden ratio to generate well-distributed hues
    const goldenRatio = 0.618033988749895;
    const hue = ((frequency * goldenRatio) % 1) * 360;
    return `hsl(${hue}, 70%, 45%)`; // Saturation and lightness fixed for good visibility
};

// Get color for amplitude (used for stroke color of pings)
const getAmplitudeColor = (normalizedValue: number) => {
    const hue = (1 - normalizedValue) * 240;
    return `hsl(${hue}, 100%, 50%)`;
};

// Create a ping icon using SignalIcon
const createPingIcon = (color: string, strokeColor: string, size: number): L.DivIcon => {
    const iconHtml = `
        <div class="relative" style="width: ${size}px; height: ${size}px;">
            <div class="absolute inset-0 flex items-center justify-center">
                <svg class="w-full h-full" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="8" fill="${color}" stroke="${strokeColor}" stroke-width="2"/>
                </svg>
            </div>
        </div>
    `;

    return L.divIcon({
        html: iconHtml,
        className: '',
        iconSize: [size, size],
        iconAnchor: [size/2, size/2],
    });
};

// Create a location estimate icon 
const createLocationEstimateIcon = (color: string): L.DivIcon => {
    const iconHtml = `
        <div class="relative" style="width: 32px; height: 32px;">
            <div class="absolute inset-0 flex items-center justify-center">
                <svg class="w-full h-full" viewBox="0 0 24 24" fill="white" stroke="${color}" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                </svg>
            </div>
        </div>
    `;

    return L.divIcon({
        html: iconHtml,
        className: '',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
    });
};

interface LoadingIndicatorProps {
    loading: boolean;
}

const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({ loading }) => {
    if (!loading) return null;
    return (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-white/95 px-4 py-2 
            rounded-full shadow-lg z-[1000] flex items-center gap-2.5 text-sm text-blue-700
            border border-blue-100">
            <ArrowPathIcon className="w-5 h-5 animate-spin" />
            <span className="font-medium">Loading map data...</span>
        </div>
    );
};

interface FrequencyLayerProps {
    frequency: number;
    pings: PingData[];
    locationEstimate: LocEstData | null;
    visible_pings: boolean;
    visible_location_estimate: boolean;
}

const FrequencyLayer: React.FC<FrequencyLayerProps> = ({
    frequency,
    pings,
    locationEstimate,
    visible_pings,
    visible_location_estimate,
}) => {
    const map = useMap();
    const markersRef = useRef<L.Marker[]>([]);
    const locationMarkerRef = useRef<L.Marker | null>(null);
    const cleanupMarkers = useCallback(() => {
        markersRef.current.forEach(marker => marker.remove());
        markersRef.current = [];
    }, []);

    // Get a distinct color for this frequency
    const frequencyColor = useMemo(() => getFrequencyColor(frequency), [frequency]);

    // Effect for ping markers
    useEffect(() => {
        if (!map || !visible_pings) {
            cleanupMarkers();
            return;
        }

        // Clean up old markers
        cleanupMarkers();

        if (pings.length > 0) {
            const amplitudes = pings.map(ping => ping.amplitude);
            const minAmplitude = Math.min(...amplitudes);
            const maxAmplitude = Math.max(...amplitudes);

            pings.forEach(ping => {
                const normalizedAmplitude = normalize(ping.amplitude, minAmplitude, maxAmplitude);
                const strokeColor = getAmplitudeColor(normalizedAmplitude);
                const size = 12 + normalizedAmplitude * 12;

                const icon = createPingIcon(frequencyColor, strokeColor, size);
                const marker = L.marker([ping.lat, ping.long], { icon }).addTo(map);

                marker.bindTooltip(`
                    <div class="p-2 font-mono text-sm">
                        <div class="font-medium text-gray-900">Frequency: ${(frequency / 1_000_000).toFixed(3)} MHz</div>
                        <div class="text-gray-600">Amplitude: ${ping.amplitude.toFixed(2)} dB</div>
                        <div class="text-gray-600">Lat: ${ping.lat.toFixed(6)}°</div>
                        <div class="text-gray-600">Long: ${ping.long.toFixed(6)}°</div>
                        <div class="text-gray-600">Time: ${new Date(ping.timestamp / 1000).toLocaleTimeString()}</div>
                    </div>
                `, { 
                    className: 'bg-white/95 border-0 shadow-lg rounded-lg',
                    offset: [0, -size/2]
                });

                markersRef.current.push(marker);
            });
        }

        return cleanupMarkers;
    }, [map, frequency, pings, visible_pings, cleanupMarkers, frequencyColor]);

    // Separate effect for location estimate marker
    useEffect(() => {
        if (!map || !visible_location_estimate || !locationEstimate) {
            if (locationMarkerRef.current) {
                locationMarkerRef.current.remove();
                locationMarkerRef.current = null;
            }
            return;
        }

        const icon = createLocationEstimateIcon(frequencyColor);
        const marker = L.marker(
            [locationEstimate.lat, locationEstimate.long],
            { icon }
        ).addTo(map);

        marker.bindTooltip(`
            <div class="p-2 font-mono text-sm">
                <div class="font-medium text-gray-900">Location Estimate</div>
                <div class="text-gray-600">Frequency: ${(frequency / 1_000_000).toFixed(3)} MHz</div>
                <div class="text-gray-600">Lat: ${locationEstimate.lat.toFixed(6)}°</div>
                <div class="text-gray-600">Long: ${locationEstimate.long.toFixed(6)}°</div>
                <div class="text-gray-600">Time: ${new Date(locationEstimate.timestamp / 1000).toLocaleTimeString()}</div>
            </div>
        `, { 
            className: 'bg-white/95 border-0 shadow-lg rounded-lg',
            offset: [0, -16]
        });

        locationMarkerRef.current = marker;

        return () => {
            if (locationMarkerRef.current) {
                locationMarkerRef.current.remove();
                locationMarkerRef.current = null;
            }
        };
    }, [map, frequency, locationEstimate, visible_location_estimate, frequencyColor]);

    return null; 

};

const DroneMarker: React.FC<{
    gpsData: GpsData | null;
    isConnected: boolean;
}> = ({ gpsData, isConnected }) => {
    const map = useMap();
    const droneMarkerRef = useRef<L.Marker | null>(null);
    const lastUpdateRef = useRef<number>(0);

    const formatLastUpdate = useCallback((timestamp: number | undefined) => {
        try {
            if (!timestamp) return 'Unknown';
            const date = new Date(timestamp);
            if (!isValid(date)) return 'Unknown';
            return formatDistanceToNow(date, { addSuffix: true, includeSeconds: true });
        } catch (err) {
            logToPython(`Error formatting timestamp: ${err}`);
            return 'Unknown';
        }
    }, []);

    const getTooltipContent = useCallback((data: GpsData | null, lastUpdate: number) => {
        if (!data) return 'Drone disconnected';
        return `
            <div class="p-2 font-mono text-sm">
                <div class="font-medium text-gray-900">Drone Status</div>
                <div class="text-gray-600">Lat: ${data.lat.toFixed(6)}°</div>
                <div class="text-gray-600">Long: ${data.long.toFixed(6)}°</div>
                <div class="text-gray-600">Alt: ${data.altitude.toFixed(1)} m</div>
                <div class="text-gray-600">Heading: ${data.heading.toFixed(1)}°</div>
                <div class="text-gray-600">Last update: ${formatLastUpdate(lastUpdate)}</div>
            </div>
        `;
    }, [formatLastUpdate]);

    const droneIconSvg = useMemo(() => `
        <div class="relative w-[32px] h-[32px]">
            <div class="absolute inset-0 flex items-center justify-center">
                <div class="drone-status-pulse"></div>
            </div>
            <div class="absolute inset-0 flex items-center justify-center">
                <div class="drone-icon-container" style="transform: rotate(var(--rotation))">
                    <svg 
                        viewBox="0 0 24 24" 
                        width="24" 
                        height="24" 
                        class="drone-icon"
                    >
                        <path d="M12 2 L14 6 L10 6 L12 2 Z" />
                        <circle cx="12" cy="12" r="4" />
                    </svg>
                </div>
            </div>
        </div>
    `, []);

    const drawDroneMarker = useCallback(
        (data: GpsData | null, isConnected: boolean) => {
            if (!map) return;

            if (!isConnected || !data) {
                if (droneMarkerRef.current) {
                    const icon = droneMarkerRef.current.getIcon();
                    if (icon instanceof L.DivIcon) {
                        icon.options.html = `<div class="drone-marker drone-marker-disconnected">${droneIconSvg}</div>`;
                        droneMarkerRef.current.setIcon(icon);
                    }
                }
                return;
            }

            const { lat, long, heading, timestamp } = data;
            lastUpdateRef.current = timestamp / 1000;

            if (!droneMarkerRef.current) {
                const icon = L.divIcon({
                    className: '',
                    html: `<div class="drone-marker drone-marker-active" style="--rotation: ${heading}deg">${droneIconSvg}</div>`,
                    iconSize: [32, 32],
                    iconAnchor: [16, 16],
                });
                const marker = L.marker([lat, long], { icon }).addTo(map);
                droneMarkerRef.current = marker;

                marker.bindTooltip('', {
                    permanent: false,
                    direction: 'bottom',
                    offset: [0, 10],
                    className: 'bg-white/95 border-0 shadow-lg rounded px-2 py-1 text-sm'
                });
                marker.setTooltipContent(getTooltipContent(data, lastUpdateRef.current));
            } else {
                droneMarkerRef.current.setLatLng([lat, long]);
                const icon = droneMarkerRef.current.getIcon();
                if (icon instanceof L.DivIcon) {
                    icon.options.html = `<div class="drone-marker drone-marker-active" style="--rotation: ${heading}deg">${droneIconSvg}</div>`;
                    droneMarkerRef.current.setIcon(icon);
                }
                if (droneMarkerRef.current.getTooltip()) {
                    droneMarkerRef.current.setTooltipContent(getTooltipContent(data, lastUpdateRef.current));
                }
            }
        },
        [map, getTooltipContent, droneIconSvg]
    );

    useEffect(() => {
        drawDroneMarker(gpsData, isConnected);

        const interval = window.setInterval(() => {
            if (droneMarkerRef.current?.getTooltip() && lastUpdateRef.current) {
                droneMarkerRef.current.setTooltipContent(getTooltipContent(gpsData, lastUpdateRef.current));
            }
        }, 1000);

        return () => {
            window.clearInterval(interval);
            if (droneMarkerRef.current) {
                droneMarkerRef.current.remove();
                droneMarkerRef.current = null;
            }
        };
    }, [gpsData, isConnected, drawDroneMarker, getTooltipContent]);

    return null;
};

const DataLayers: React.FC = () => {
    const context = useContext(GlobalAppContext);
    if (!context) throw new Error('DataLayers must be in GlobalAppProvider');

    const { gpsData, connectionStatus, frequencyData, frequencyVisibility, frequencyData1, frequencyVisibility1 } = context;
    const [isLoading, setIsLoading] = useState(false);
    const loadingTimeoutRef = useRef<TimeoutRef | null>(null);
    const map = useMap();

    useEffect(() => {
        if (!map) return;

        const handleMoveStart = () => {
            if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
            setIsLoading(true);
        };

        const handleMoveEnd = () => {
            loadingTimeoutRef.current = setTimeout(() => setIsLoading(false), 1000);
        };

        map.on('movestart', handleMoveStart);
        map.on('moveend', handleMoveEnd);
        map.on('zoomstart', handleMoveStart);
        map.on('zoomend', handleMoveEnd);

        return () => {
            map.off('movestart', handleMoveStart);
            map.off('moveend', handleMoveEnd);
            map.off('zoomstart', handleMoveStart);
            map.off('zoomend', handleMoveEnd);
            if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
        };
    }, [map]);


    return (
        <>
            <LoadingIndicator loading={isLoading} />
            <DroneMarker gpsData={gpsData} isConnected={connectionStatus === 1} />

            {/* Actual layers rendering */}
            {(frequencyVisibility1 ?? []).map(({ frequency, visible_pings }) => (
                <FrequencyLayer
                    key={frequency}
                    frequency={frequency}
                    pings={frequencyData1[frequency]?.pings || []}
                    locationEstimate={frequencyData1[frequency]?.locationEstimate || null}
                    visible_pings={visible_pings} 
                    visible_location_estimate={true}
                />
            ))}

            {frequencyVisibility.map(({ frequency, visible_pings, visible_location_estimate }) => (
                <FrequencyLayer
                    key={frequency}
                    frequency={frequency}
                    pings={frequencyData[frequency]?.pings || []}
                    locationEstimate={frequencyData[frequency]?.locationEstimate || null}
                    visible_pings={visible_pings}
                    visible_location_estimate={visible_location_estimate}
                />
            ))}



        </>
    );
};

export default DataLayers;


