import React from 'react';

interface SingleSelectDropdownProps {
  options: { id: string, name: string }[];
  selectedOption: string; // The selected id, not the name
  setSelectedOption: (option: string) => void;
  label: string;
}

const SingleSelectDropdown: React.FC<SingleSelectDropdownProps> = ({ options, selectedOption, setSelectedOption, label }) => {

  // Handle the selection change and pass the selected organization id
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedId = e.target.value;
    setSelectedOption(selectedId);
  };

  return (
    <div>
      <label>{label}</label>
      <select value={selectedOption} onChange={handleChange}>
        <option value="">Select an organization</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.name}
          </option>
        ))}
      </select>
    </div>
  );
};

export default SingleSelectDropdown;
