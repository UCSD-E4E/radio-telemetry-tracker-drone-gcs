import React from 'react';
import FrequencyLayersControl from './cards/FrequencyLayersControl';
import TrackingSession  from './cards/TrackingSession';
import Card from '../common/Card';


const FrequencyManager: React.FC = () => {
    return (
        <Card title="Frequency Manager">
            <FrequencyLayersControl />
            <TrackingSession />
        </Card>
    );
};

export default FrequencyManager;
