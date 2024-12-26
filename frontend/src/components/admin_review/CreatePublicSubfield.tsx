import React, { useState } from 'react';
import axiosInstance from '../../axiosInstance';

const PublicSubfield: React.FC = () => {
  const [subfieldName, setSubfieldName] = useState<string>('');
  const [message, setMessage] = useState<string>('');

  const handleCreateSubfield = async () => {
    if (!subfieldName) {
      setMessage('Subfield name is required.');
      return;
    }

    try {
      const response = await axiosInstance.post('/create_public_subfield', {
        name: subfieldName,
      });
      setMessage(response.data.message || `Public subfield '${subfieldName}' created successfully.`);
      setSubfieldName(''); // Clear the input field after creation
    } catch (err) {
      console.error('Error creating subfield:', err);
      setMessage('An error occurred while creating the subfield.');
    }
  };

  return (
    <div>
      <h3>Create a New Public Subfield</h3>
      <input
        type="text"
        value={subfieldName}
        onChange={(e) => setSubfieldName(e.target.value)}
        placeholder="Enter subfield name"
      />
      <button onClick={handleCreateSubfield}>Create Subfield</button>
      {message && <p>{message}</p>}
    </div>
  );
};

export default PublicSubfield;
