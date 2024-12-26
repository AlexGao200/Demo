import React, { useEffect, useState } from 'react';
import axiosInstance from '../../axiosInstance';
import SingleSelectDropdown from './SingleSelectDropdown';
import { Subfield } from '../../types/MetadataTypes'; // Import Subfield type

const CreateAreaForSubfield: React.FC = () => {
  const [subfields, setSubfields] = useState<Subfield[]>([]);
  const [selectedSubfieldId, setSelectedSubfieldId] = useState<string>(''); // Selected subfield ID
  const [areaName, setAreaName] = useState<string>('');
  const [message, setMessage] = useState<string>('');

  // Fetch subfields from the backend
  useEffect(() => {
    const fetchSubfields = async () => {
      try {
        const response = await axiosInstance.get('/get_public_metadata');
        const subfieldData = response.data.subfields;
        setSubfields(subfieldData.map((subfield: any) => ({
          id: subfield.id,
          name: subfield.name,
        })));
      } catch (err) {
        console.error('Error fetching subfields:', err);
        setMessage('Error fetching subfields.');
      }
    };

    fetchSubfields();
  }, []);

  const handleAddFilterDimValue = async () => {
    if (!selectedSubfieldId || !areaName) {
      setMessage('Subfield and area name are required.');
      return;
    }

    try {
      const response = await axiosInstance.post('/add_area_to_subfield', {
        subfield_id: selectedSubfieldId,
        area_name: areaName,
      });
      setMessage(response.data.message || 'Area added successfully.');
      setSelectedSubfieldId('');
      setAreaName(''); // Clear inputs after submission
    } catch (err) {
      console.error('Error adding area to subfield:', err);
      setMessage('An error occurred while adding the area.');
    }
  };

  return (
    <div>
      <h3>Add Area to Subfield</h3>
      <SingleSelectDropdown
        options={subfields.map(subfield => ({ id: subfield.id, name: subfield.name }))}
        selectedOption={selectedSubfieldId}
        setSelectedOption={setSelectedSubfieldId}
        label="Select Subfield"
      />
      <br />
      <label>
        Area Name:
        <input
          type="text"
          value={areaName}
          onChange={(e) => setAreaName(e.target.value)}
          placeholder="Enter Area Name"
        />
      </label>
      <br />
      <button onClick={handleAddFilterDimValue}>Add Area</button>
      {message && <p>{message}</p>}
    </div>
  );
};

export default CreateAreaForSubfield;
