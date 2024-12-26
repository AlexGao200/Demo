import React from 'react';

interface MultiSelectDropdownProps {
  options: { id: string; name: string }[];
  selectedOptions: string[];
  setSelectedOptions: (options: string[]) => void;
  label: string;
}

const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  options,
  selectedOptions,
  setSelectedOptions,
  label,
}) => {
  const handleOptionChange = (optionId: string) => {
    const updatedOptions = selectedOptions.includes(optionId)
      ? selectedOptions.filter((id) => id !== optionId)
      : [...selectedOptions, optionId];
    setSelectedOptions(updatedOptions);
  };

  return (
    <div className="multi-select-dropdown">
      <h3>{label}</h3>
      <div className="options-container">
        {options.map((option) => (
          <label key={option.id} className="option-label">
            <input
              type="checkbox"
              checked={selectedOptions.includes(option.id)}
              onChange={() => handleOptionChange(option.id)}
            />
            {option.name}
          </label>
        ))}
      </div>
      <style jsx>{`
        .multi-select-dropdown {
          margin-bottom: 1rem;
        }
        .options-container {
          max-height: 200px;
          overflow-y: auto;
          border: 1px solid #ccc;
          padding: 0.5rem;
        }
        .option-label {
          display: block;
          margin-bottom: 0.5rem;
        }
        input[type="checkbox"] {
          margin-right: 0.5rem;
        }
      `}</style>
    </div>
  );
};

export default MultiSelectDropdown;
