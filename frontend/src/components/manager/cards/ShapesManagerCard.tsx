import React from 'react';
import { useMapShapes } from '../../../context/MapShapesContext';
import { EyeIcon, EyeSlashIcon, TrashIcon } from '@heroicons/react/24/outline';

const ShapesManagerCard: React.FC = () => {
    const { shapes, toggleShapeVisibility, deleteShape } = useMapShapes();

    if (shapes.length === 0) {
        return (
            <div className="p-3 text-center text-gray-500 italic">
                No shapes drawn yet. Use the drawing tools on the map to create shapes.
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {shapes.map(shape => (
                <div key={shape.id} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2">
                        <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: shape.color }}
                        ></div>
                        <span className="text-sm font-medium">{shape.name || `${shape.type.charAt(0).toUpperCase() + shape.type.slice(1)}`}</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => toggleShapeVisibility(shape.id)}
                            className="p-1 text-gray-500 hover:text-gray-700 rounded-md hover:bg-gray-100"
                            title={shape.visible ? "Hide shape" : "Show shape"}
                        >
                            {shape.visible ? (
                                <EyeIcon className="w-5 h-5" />
                            ) : (
                                <EyeSlashIcon className="w-5 h-5" />
                            )}
                        </button>
                        <button
                            onClick={() => deleteShape(shape.id)}
                            className="p-1 text-gray-500 hover:text-red-700 rounded-md hover:bg-gray-100"
                            title="Delete shape"
                        >
                            <TrashIcon className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
};

export default ShapesManagerCard;