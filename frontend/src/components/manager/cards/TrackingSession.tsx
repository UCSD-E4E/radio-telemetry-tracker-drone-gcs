import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";

const TrackingSession: React.FC = () => {
    const [sessionName, setSessionName] = useState("");
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [frequencies, setFrequencies] = useState<any[]>([]);
    const [searchName, setSearchName] = useState("");
    const { toast } = useToast();

    const handleSaveSession = async () => {
        if (!sessionName) return;
        try {
            const success = await window.backend.add_tracking_session(sessionName, "Saved session");
            if (success) {
                toast({ title: "Session saved successfully!" });
                setIsModalOpen(false);
            } else {
                toast({ title: "Failed to save session", variant: "destructive" });
            }
        } catch (error) {
            console.error("Error saving session:", error);
            toast({ title: "Error saving session", variant: "destructive" });
        }
    };

    const handleLoadSession = async () => {
        if (!searchName) return;
        try {
            const data = await window.backend.get_frequencies_by_session_name(searchName);
            if (data.length > 0) {
                setFrequencies(data);
            } else {
                toast({ title: "No data found for this session" });
                setFrequencies([]);
            }
        } catch (error) {
            console.error("Error loading session:", error);
            toast({ title: "Error loading session", variant: "destructive" });
        }
    };

    return (
        <div className="p-4">
            <Button onClick={() => setIsModalOpen(true)}>Save Session</Button>
            <Modal open={isModalOpen} onClose={() => setIsModalOpen(false)}>
                <div className="p-4">
                    <h2 className="text-lg font-semibold mb-2">Enter Tracking Session Name</h2>
                    <Input value={sessionName} onChange={(e) => setSessionName(e.target.value)} placeholder="Session Name" />
                    <Button onClick={handleSaveSession} className="mt-2">Save</Button>
                </div>
            </Modal>
            
            <div className="mt-4">
                <Input value={searchName} onChange={(e) => setSearchName(e.target.value)} placeholder="Search Tracking Session" />
                <Button onClick={handleLoadSession} className="mt-2">Load</Button>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                {frequencies.map((freq, index) => (
                    <Card key={index}>
                        <CardContent>
                            <p><strong>Frequency:</strong> {freq.frequency} Hz</p>
                            <p><strong>Signal Strength:</strong> {freq.signal_strength}</p>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
};

export default TrackingSession;
