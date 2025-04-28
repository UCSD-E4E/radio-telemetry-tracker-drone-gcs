import React, { useContext, useState } from 'react';
import { 
    PencilSquareIcon, 
    XCircleIcon, 
    RectangleGroupIcon,
    // XMarkIcon
} from '@heroicons/react/24/outline';
import { GlobalAppContext } from '../../context/globalAppContextDef';


const ControlButton: React.FC<{
    label: string;
    onClick: () => void;
    icon: React.ReactNode;
    active?: boolean;
    className?: string;
    description?: string;
}> = ({ label, onClick, icon, active, className = '', description }) => (
    <button
        onClick={onClick}
        className={`group relative p-2.5 rounded-lg transition-all duration-200 ${
            active 
                ? 'bg-blue-100 text-blue-600 ring-2 ring-blue-500 ring-opacity-50' 
                : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
        } ${className}`}
        title={label}
    >
        {icon}
        <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 min-w-[150px] 
            opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none">
            <div className="bg-gray-900 text-white p-2 rounded-lg shadow-lg">
                <div className="font-medium">{label}</div>
                {description && (
                    <div className="text-xs text-gray-300 mt-1">{description}</div>
                )}
            </div>
        </div>
    </button>
);

const MapDrawingControls: React.FC = () => {
    const context = useContext(GlobalAppContext);
    if (!context) throw new Error('MapDrawingControls must be in GlobalAppProvider');

    const [activeDrawTool, setActiveDrawTool] = useState<string | null>(null);

    const handleDrawToolClick = (tool: string) => {
        if (activeDrawTool === tool) {
            // Toggle off if already active
            setActiveDrawTool(null);
        } else {
            setActiveDrawTool(tool);
        }
    };

    return (
        <div className="fixed left-4 top-1/2 -translate-y-1/2 flex flex-col gap-2 z-[2001]">
            <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg p-2.5 space-y-2.5 border border-gray-200">
                <ControlButton
                    label="Draw Polygon"
                    description="Draw polygon shapes on the map"
                    onClick={() => handleDrawToolClick('polygon')}
                    icon={<RectangleGroupIcon className="w-6 h-6" />}
                    active={activeDrawTool === 'polygon'}
                />
                <ControlButton
                    label="Draw Line"
                    description="Draw lines on the map"
                    onClick={() => handleDrawToolClick('polyline')}
                    icon={<PencilSquareIcon className="w-6 h-6" />}
                    active={activeDrawTool === 'polyline'}
                />
                <ControlButton
                    label="Draw Circle"
                    description="Draw circles on the map"
                    onClick={() => handleDrawToolClick('circle')}
                    icon={<XCircleIcon className="w-6 h-6" />}
                    active={activeDrawTool === 'circle'}
                />
            </div>
        </div>
    );
};

export default MapDrawingControls;