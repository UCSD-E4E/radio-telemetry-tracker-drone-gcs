import React, { useState, useContext } from "react";
import { GlobalAppContext } from "../../../context/globalAppContextDef";
import Card from "../../common/Card";

const TrackingSessionComponent: React.FC = () => {
    const context = useContext(GlobalAppContext);

    const save_frequencies_to_session = context?.save_frequencies_to_session ?? (() => Promise.resolve(-1));
    const get_all_tracking_session_names = context?.get_all_tracking_session_names ?? (() => Promise.resolve([]));
    const get_frequencies_by_session = context?.get_frequencies_by_session ?? (() => Promise.resolve([]));
    const frequencyData = context?.frequencyData ?? {};

    const [sessionName, setSessionName] = useState("");
    const [sessionDate, setSessionDate] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [showSuccessMessage, setShowSuccessMessage] = useState(false);
    const [allSessionNames, setAllSessionNames] = useState<string[]>([]);
    const [showSessionListModal, setShowSessionListModal] = useState(false);
    const [loadedSessionNames, setLoadedSessionNames] = useState<string[]>([]);

    const convertFrequencyDataToTrackingSession = (frequencyData: any) => {
        return Object.entries(frequencyData).flatMap(([freq, data]: any) =>
            data.pings.map((ping: any) => ({
                frequency: Number(freq),
                data_type: "ping",
                latitude: ping.lat,
                longitude: ping.long,
                amplitude: ping.amplitude ?? null,
                timestamp: ping.timestamp,
                packet_idts: ping.packet_id,
            }))
        );
    };

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

    const handleOpenLoadSession = async () => {
        setIsLoading(true);
        try {
            const names = await get_all_tracking_session_names();
            setAllSessionNames(names);
            setShowSessionListModal(true);
        } catch (err) {
            console.error("Error fetching session names:", err);
            alert("Failed to fetch session list.");
        }
        setIsLoading(false);
    };

    const handleClickSessionName = async (name: string) => {
        setIsLoading(true);
        try {
            await get_frequencies_by_session(name); // this should update map already
            setLoadedSessionNames(prev => [...new Set([...prev, name])]);
            setShowSessionListModal(false);
        } catch (err) {
            console.error("Error loading session:", err);
            alert("Failed to load session.");
        }
        setIsLoading(false);
    };

    const handleRemoveLoadedSession = (name: string) => {
        // You’ll add the logic to remove from map later
        setLoadedSessionNames(prev => prev.filter(n => n !== name));
    };

    return (
        <div className="modal">
            <div className="modal-content">
                <h2>Manage Tracking Session</h2>

                {/* Save Section */}
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
                    <button onClick={handleOpenLoadSession} disabled={isLoading} className="load-button">
                        {isLoading ? "Loading..." : "Load Session"}
                    </button>
                </div>

                {showSuccessMessage && (
                    <div className="success-message">
                        Tracking session successfully saved!
                    </div>
                )}

                {/* Loaded Sessions Display */}
                {loadedSessionNames.length > 0 && (
                    <Card title="Loaded Sessions">
                        <ul className="loaded-session-list">
                            {loadedSessionNames.map((name) => (
                                <li key={name} className="loaded-session-item">
                                    {name}
                                    <button onClick={() => handleRemoveLoadedSession(name)} className="remove-btn">❌</button>
                                </li>
                            ))}
                        </ul>
                    </Card>
                )}

                {/* Modal to pick a session to load */}
                {showSessionListModal && (
                    <div className="overlay">
                        <div className="modal popup">
                            <h3>Select Session to Load</h3>
                            <ul className="session-list">
                                {allSessionNames.map((name) => (
                                    <li key={name} className="session-list-item" onClick={() => handleClickSessionName(name)}>
                                        {name}
                                    </li>
                                ))}
                            </ul>
                            <button onClick={() => setShowSessionListModal(false)} className="close-btn">Close</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default TrackingSessionComponent;
