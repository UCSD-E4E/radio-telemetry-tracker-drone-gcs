import React, { useState, useContext } from "react";
import { GlobalAppContext } from "../../../context/globalAppContextDef";
import Card from "../../common/Card";
import { XMarkIcon } from "@heroicons/react/24/solid";

const TrackingSessionComponent: React.FC = () => {
    const context = useContext(GlobalAppContext);

    const save_frequencies_to_session = context?.save_frequencies_to_session ?? (() => Promise.resolve(-1));
    const get_all_tracking_session_names = context?.get_all_tracking_session_names ?? (() => Promise.resolve([]));
    const get_frequencies_by_session = context?.get_frequencies_by_session ?? (() => Promise.resolve([]));
    const removeTrackingSessionFromMap = context?.removeTrackingSessionFromMap;
    
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
            await get_frequencies_by_session(name);
            setLoadedSessionNames(prev => [...new Set([...prev, name])]);
            setShowSessionListModal(false);
        } catch (err) {
            console.error("Error loading session:", err);
            alert("Failed to load session.");
        }
        setIsLoading(false);
    };

    const handleRemoveLoadedSession = (name: string) => {
        setLoadedSessionNames(prev => prev.filter(n => n !== name));
        removeTrackingSessionFromMap?.(name);
    };

    return (
        <div className="p-4 space-y-6">
            <Card title="Tracking Session">
                <div className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <input
                            type="text"
                            placeholder="Session Name"
                            value={sessionName}
                            onChange={(e) => setSessionName(e.target.value)}
                            className="input input-bordered w-full"
                        />
                        <input
                            type="date"
                            value={sessionDate}
                            onChange={(e) => setSessionDate(e.target.value)}
                            className="input input-bordered w-full"
                        />
                    </div>

                    <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-2 sm:space-y-0">
                        <button
                            onClick={handleSave}
                            disabled={isLoading}
                            className="btn btn-primary w-full sm:w-auto"
                        >
                            {isLoading ? "Saving..." : "Save Session"}
                        </button>
                        <button
                            onClick={handleOpenLoadSession}
                            disabled={isLoading}
                            className="btn btn-secondary w-full sm:w-auto"
                        >
                            {isLoading ? "Loading..." : "Load Session"}
                        </button>
                    </div>

                    {showSuccessMessage && (
                        <div className="text-green-600 text-sm">
                            ✅ Tracking session successfully saved!
                        </div>
                    )}
                </div>
            </Card>

            {loadedSessionNames.length > 0 && (
                <Card title="Loaded Sessions">
                    <ul className="space-y-2">
                        {loadedSessionNames.map((name) => (
                            <li key={name} className="flex justify-between items-center p-2 rounded-lg border bg-white shadow-sm hover:shadow-md">
                                <span className="text-sm text-gray-800">{name}</span>
                                <button
                                    onClick={() => handleRemoveLoadedSession(name)}
                                    className="text-red-500 hover:text-red-700 p-1 rounded-full hover:bg-red-100 transition"
                                    aria-label="Remove session"
                                >
                                    <XMarkIcon className="h-4 w-4" />
                                </button>
                            </li>
                        ))}
                    </ul>
                </Card>
            )}

            {showSessionListModal && (
                <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-xl space-y-4">
                        <h3 className="text-lg font-semibold">Select Session to Load</h3>
                        <ul className="divide-y divide-gray-200">
                            {allSessionNames.map((name) => (
                                <li
                                    key={name}
                                    className="py-2 px-2 hover:bg-gray-100 cursor-pointer text-sm"
                                    onClick={() => handleClickSessionName(name)}
                                >
                                    {name}
                                </li>
                            ))}
                        </ul>
                        <button
                            onClick={() => setShowSessionListModal(false)}
                            className="mt-4 btn btn-outline w-full"
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default TrackingSessionComponent;
