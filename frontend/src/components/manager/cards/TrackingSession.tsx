import React, { useContext } from 'react';
import { GlobalAppContext } from  '../../../context/globalAppContextDef';

const ModalComponent = () => {
    const { save_frequencies_to_session } = useContext(GlobalAppContext);

    const handleSave = async () => {
        try {
            const result = await save_frequencies_to_session('sessionName', 'sessionDate', frequenciesData);
            console.log(result);
        } catch (error) {
            console.error('Error saving frequencies:', error);
        }
    };

    return (
        <div>
            <button onClick={handleSave}>Save Frequencies</button>
        </div>
    );
};

export default ModalComponent;
