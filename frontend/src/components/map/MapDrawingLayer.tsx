import React, { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import 'leaflet-draw/dist/leaflet.draw.css';
import L from 'leaflet';
import 'leaflet-draw';
import { useMapShapes } from '../../context/MapShapesContext';

// Add these type definitions to fix the TypeScript error
declare module 'leaflet' {
  namespace Control {
    class Draw extends L.Control {
      constructor(options?: DrawConstructorOptions);
    }
    
    interface DrawConstructorOptions {
      draw?: {
        polyline?: boolean | object;
        polygon?: boolean | object;
        rectangle?: boolean | object;
        circle?: boolean | object;
        marker?: boolean | object;
        circlemarker?: boolean | object;
      };
      edit?: {
        featureGroup: L.FeatureGroup;
        remove?: boolean;
        edit?: boolean;
      };
    }
  }
  
  namespace Draw {
    namespace Event {
      const CREATED: string;
      const EDITED: string;
      const DELETED: string;
      const DRAWSTART: string;
      const DRAWSTOP: string;
      const DRAWVERTEX: string;
      const EDITSTART: string;
      const EDITMOVE: string;
      const EDITRESIZE: string;
      const EDITVERTEX: string;
      const EDITSTOP: string;
      const DELETESTART: string;
      const DELETESTOP: string;
    }
    
    class Polygon {
      constructor(map: L.Map, options?: any);
      enable(): void;
      disable(): void;
    }
    
    class Polyline {
      constructor(map: L.Map, options?: any);
      enable(): void;
      disable(): void;
    }
    
    class Circle {
      constructor(map: L.Map, options?: any);
      enable(): void;
      disable(): void;
    }
  }
  
  interface Map {
    drawHandler?: any;
  }
}

const MapDrawingLayer: React.FC = () => {
    const map = useMap();
    const { activeDrawTool, setActiveDrawTool, addShape } = useMapShapes();
    
    useEffect(() => {
        // Create FeatureGroup to store drawn items
        const drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);
        
        // Initialize the draw control and pass it the FeatureGroup
        // const drawControl = new L.Control.Draw({
        //     draw: {
        //         polyline: false,
        //         polygon: false,
        //         rectangle: false,
        //         circle: false,
        //         marker: false,
        //         circlemarker: false
        //     },
        //     edit: {
        //         featureGroup: drawnItems,
        //         remove: false,
        //         edit: false
        //     }
        // });
        
        // Create handlers for shape creation events
        const handleShapeCreated = (e: any) => {
            const layer = e.layer;
            drawnItems.addLayer(layer);
            
            // Generate shape data based on type
            let coordinates;
            const type = e.layerType;
            
            if (type === 'polygon') {
                coordinates = layer.getLatLngs()[0].map((latlng: L.LatLng) => [latlng.lat, latlng.lng]);
            } else if (type === 'polyline') {
                coordinates = layer.getLatLngs().map((latlng: L.LatLng) => [latlng.lat, latlng.lng]);
            } else if (type === 'circle') {
                coordinates = {
                    center: [layer.getLatLng().lat, layer.getLatLng().lng],
                    radius: layer.getRadius()
                };
            }
            
            // Add shape to context
            addShape({
                type: type as any,
                coordinates,
                visible: true,
                name: `${type.charAt(0).toUpperCase() + type.slice(1)} ${Date.now().toString().slice(-4)}`,
                color: '#3388ff' // Default leaflet color
            });
            
            // Reset active draw tool
            setActiveDrawTool(null);
        };
        
        map.on(L.Draw.Event.CREATED, handleShapeCreated);
        
        // Clean up on unmount
        return () => {
            map.removeLayer(drawnItems);
            map.off(L.Draw.Event.CREATED, handleShapeCreated);
        };
    }, [map, addShape, setActiveDrawTool]);
    
    // Handle active drawing tool changes
    useEffect(() => {
        if (!activeDrawTool) return;
        
        // Start drawing based on the active tool
        if (activeDrawTool === 'polygon') {
            map.drawHandler = new L.Draw.Polygon(map);
            map.drawHandler.enable();
        } else if (activeDrawTool === 'polyline') {
            map.drawHandler = new L.Draw.Polyline(map);
            map.drawHandler.enable();
        } else if (activeDrawTool === 'circle') {
            map.drawHandler = new L.Draw.Circle(map);
            map.drawHandler.enable();
        }
        
        // Clean up on tool change
        return () => {
            // Disable any active drawing
            if (map.drawHandler && typeof map.drawHandler.disable === 'function') {
                map.drawHandler.disable();
            }
        };
    }, [activeDrawTool, map]);
    
    return null;
};

export default MapDrawingLayer;