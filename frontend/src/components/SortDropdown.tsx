import React from 'react';

interface SortDropdownProps {
  sortField: string;
  sortOrder: 'asc' | 'desc';
  onSortChange: (field: string, order: 'asc' | 'desc') => void;
}

const SortDropdown: React.FC<SortDropdownProps> = ({ sortField, sortOrder, onSortChange }) => {

  const handleFieldChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const field = event.target.value;
    onSortChange(field, sortOrder); // Call the parent's sorting handler
  };

  const handleOrderChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const order = event.target.value as 'asc' | 'desc';
    onSortChange(sortField, order); // Call the parent's sorting handler
  };

  return (
    <div className="sort-dropdown">
      <label htmlFor="sortField">Sort by: </label>
      <select id="sortField" value={sortField} onChange={handleFieldChange}>
        <option value="title">Title</option>
        <option value="organization">Organization</option>
        <option value="filter_dimensions.name">Category</option>
      </select>

    </div>
  );
};

export default SortDropdown;
