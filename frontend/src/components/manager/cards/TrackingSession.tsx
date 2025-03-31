import React, { useState, useContext } from "react";
import { GlobalAppContext } from "../../../context/globalAppContextDef";
import type { TrackingSession, FrequencyData, PingData, FrequencyRecord } from "../../../types/global";
import Card from "../../common/Card";

const TrackingSessionComponent: React.FC = () => {
    const context = useContext(GlobalAppContext);

    // Ensure context methods exist
    const save_frequencies_to_session = context?.save_frequencies_to_session ?? (() => Promise.resolve(-1));
    const get_frequencies_by_session = context?.get_frequencies_by_session ?? (() => Promise.resolve([]));

    // Global frequency data
    const frequencyData = context?.frequencyData ?? {};

    const [sessionName, setSessionName] = useState("");
    const [sessionDate, setSessionDate] = useState("");
    const [loadedData, setLoadedData] = useState<TrackingSession | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [showSuccessMessage, setShowSuccessMessage] = useState(false);

    // Function to map FrequencyData to TrackingSession format
    const convertFrequencyDataToTrackingSession = (frequencyData: FrequencyData): TrackingSession => {
        return Object.entries(frequencyData).flatMap(([freq, data]) => 
            data.pings.map((ping: PingData): FrequencyRecord => ({
                frequency: Number(freq),  
                data_type: "ping",
                latitude: ping.lat,
                longitude: ping.long,
                amplitude: ping.amplitude ?? null,
                timestamp: ping.timestamp,
            }))
        );
    };

    // Handler for saving frequency data
    const handleSave = async () => {
        if (!sessionName || !sessionDate) {
            alert("Please provide both session name and date.");
            return;
        }

        const trackingSession = convertFrequencyDataToTrackingSession(frequencyData);

        if (trackingSession.length === 0) {
            alert("No frequency data available to save.");
            return;
        }

        setIsLoading(true);

        const response = await save_frequencies_to_session(sessionName, sessionDate, trackingSession);

        if (response === -1) {
            alert("Failed to save session.");
        } else {
            setShowSuccessMessage(true);
            setTimeout(() => setShowSuccessMessage(false), 3000);
        }

        setIsLoading(false);
    };

    // Handler for loading frequency data
    const handleLoad = async () => {
        if (!sessionName) {
            alert("Please provide a session name to load.");
            return;
        }

        setIsLoading(true);

        try {
            const data = await get_frequencies_by_session(sessionName);

            if (data.length === 0) {
                alert("No data found for this session.");
            } else {
                setLoadedData(data);
            }
        } catch (error) {
            console.error("Error loading session:", error);
            alert("Failed to load session.");
        }

        setIsLoading(false);
    };

    return (
        <div className="modal">
            <div className="modal-content">
                <h2>Manage Tracking Session</h2>

                <input 
                    type="text" 
                    placeholder="Session Name" 
                    value={sessionName} 
                    onChange={(e) => setSessionName(e.target.value)} 
                    className="input-field"
                />
                <input 
                    type="date" 
                    value={sessionDate} 
                    onChange={(e) => setSessionDate(e.target.value)} 
                    className="input-field"
                />

                <div className="modal-actions">
                    <button onClick={handleSave} disabled={isLoading} className="save-button">
                        {isLoading ? "Saving..." : "Save Session"}
                    </button>
                    <button onClick={handleLoad} disabled={isLoading} className="load-button">
                        {isLoading ? "Loading..." : "Load Session"}
                    </button>
                </div>

                {showSuccessMessage && (
                    <div className="success-message">
                        Tracking session successfully saved!
                    </div>
                )}

                {loadedData && loadedData.length > 0 && (
                    <Card title="Loaded Frequency Data">
                        <div className="frequency-list">
                            {loadedData.map((record, index) => (
                                <div key={index} className="frequency-record">
                                    <p><strong>Frequency:</strong> {record.frequency / 1_000_000} MHz</p>
                                    <p><strong>Data Type:</strong> {record.data_type}</p>
                                    <p><strong>Latitude:</strong> {record.latitude}</p>
                                    <p><strong>Longitude:</strong> {record.longitude}</p>
                                    <p><strong>Amplitude:</strong> {record.amplitude ?? "N/A"}</p>
                                    <p><strong>Timestamp:</strong> {new Date(record.timestamp).toLocaleString()}</p>
                                </div>
                            ))}
                        </div>
                    </Card>
                )}
            </div>
        </div>
    );
};

export default TrackingSessionComponent;
