import { useState, useEffect } from 'react';

export const useSimulatorShortcut = () => {
    const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);

    useEffect(() => {
        const handleKeyDown = (e: globalThis.KeyboardEvent) => {
            // Check for Ctrl+Alt+S (Windows/Linux) or Cmd+Alt+S (Mac)
            if ((e.ctrlKey || e.metaKey) && e.altKey && e.key.toLowerCase() === 's') {
                e.preventDefault(); // Prevent default browser behavior
                setIsSimulatorOpen(prev => !prev);
            }

            // Check for Cmd+Shift+S (Mac)
            if (e.metaKey && e.shiftKey && e.key.toLowerCase() === 's') {
                e.preventDefault(); // Prevent default browser behavior
                setIsSimulatorOpen(prev => !prev);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    return {
        isSimulatorOpen,
        setIsSimulatorOpen
    };
}; 