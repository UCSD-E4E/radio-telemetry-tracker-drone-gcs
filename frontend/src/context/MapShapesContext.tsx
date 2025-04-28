import React, { createContext, useContext, useState } from 'react';

// Define shape types
export type MapShape = {
    id: string;
    type: 'polygon' | 'polyline' | 'circle';
    coordinates: any; // This will depend on the shape type
    visible: boolean;
    name: string;
    color: string;
};

type MapShapesContextType = {
    shapes: MapShape[];
    addShape: (shape: Omit<MapShape, 'id'>) => void;
    deleteShape: (id: string) => void;
    toggleShapeVisibility: (id: string) => void;
    activeDrawTool: string | null;
    setActiveDrawTool: (tool: string | null) => void;
};

export const MapShapesContext = createContext<MapShapesContextType | null>(null);

export const MapShapesProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
    const [shapes, setShapes] = useState<MapShape[]>([]);
    const [activeDrawTool, setActiveDrawTool] = useState<string | null>(null);
    
    const addShape = (shape: Omit<MapShape, 'id'>) => {
        const id = `shape-${Date.now()}`;
        setShapes(prev => [...prev, { ...shape, id }]);
    };
    
    const deleteShape = (id: string) => {
        setShapes(prev => prev.filter(shape => shape.id !== id));
    };
    
    const toggleShapeVisibility = (id: string) => {
        setShapes(prev => prev.map(shape => 
            shape.id === id ? { ...shape, visible: !shape.visible } : shape
        ));
    };
    
    return (
        <MapShapesContext.Provider value={{ 
            shapes, 
            addShape, 
            deleteShape, 
            toggleShapeVisibility,
            activeDrawTool,
            setActiveDrawTool
        }}>
            {children}
        </MapShapesContext.Provider>
    );
};

export const useMapShapes = () => {
    const context = useContext(MapShapesContext);
    if (!context) {
        throw new Error('useMapShapes must be used within a MapShapesProvider');
    }
    return context;
};