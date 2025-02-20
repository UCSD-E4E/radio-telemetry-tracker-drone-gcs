import React, { useState } from "react";

// Simplified TrackingSession component without UI components
const TrackingSession: React.FC = () => {
    const [sessionName, setSessionName] = useState("");
    const [frequencies, setFrequencies] = useState<any[]>([]); // Use an array to store frequencies
    const [searchName, setSearchName] = useState("");

    const handleSaveSession = async () => {
        if (!sessionName) return;
        try {
            const success = await window.backend.add_tracking_session(sessionName, "Saved session");
            if (success) {
                console.log("Session saved successfully!");
            } else {
                console.log("Failed to save session");
            }
        } catch (error) {
            console.error("Error saving session:", error);
        }
    };

    const handleLoadSession = async () => {
        if (!searchName) return;
        try {
            // Step 1: Get all sessions
            const sessions = await window.backend.get_tracking_sessions();
            
            // Step 2: Find the session by name
            const session = sessions.find(s => s.name === searchName);
            
            if (!session) {
                console.log("Session not found");
                return;
            }
    
            // Step 3: Get frequencies by session ID
            const data = await window.backend.get_frequencies_by_session(session.id);
            
            // Step 4: Convert FrequencyData to an array and update state
            const frequencyList = Object.entries(data).map(([frequency, details]) => ({
                frequency,
                ...details,
            }));
            
            setFrequencies(frequencyList);
        } catch (error) {
            console.error("Error loading session:", error);
        }
    };

    return (
        <div>
            <div>
                <input
                    type="text"
                    value={sessionName}
                    onChange={(e) => setSessionName(e.target.value)}
                    placeholder="Enter session name"
                />
                <button onClick={handleSaveSession}>Save Session</button>
            </div>

            <div>
                <input
                    type="text"
                    value={searchName}
                    onChange={(e) => setSearchName(e.target.value)}
                    placeholder="Search Tracking Session"
                />
                <button onClick={handleLoadSession}>Load</button>
            </div>

            <div>
                {frequencies.length > 0 ? (
                    frequencies.map((freq, index) => (
                        <div key={index}>
                            <p><strong>Frequency:</strong> {freq.frequency} Hz</p>
                            <p><strong>Signal Strength:</strong> {freq.signal_strength}</p>
                        </div>
                    ))
                ) : (
                    <p>No frequencies to display</p>
                )}
            </div>
        </div>
    );
};

export default TrackingSession;
