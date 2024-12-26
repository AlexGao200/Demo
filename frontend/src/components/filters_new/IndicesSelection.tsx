import React, { useState, useCallback, memo, useMemo } from 'react';
import { Index } from '../../types/FilterTypes';
import { NavigationCallbacks } from './BaseFilter';
import { useFetchIndices } from '../../hooks/useFetchIndices';
import { useUnifiedFilter } from '../../context/UnifiedFilterContext';
import "../../styles/IndicesSelection.css";

interface IndicesSelectionProps extends NavigationCallbacks {
  selectedIndices: Index[];
  setSelectedIndices: React.Dispatch<React.SetStateAction<Index[]>>;
}

const IndicesSelection: React.FC<IndicesSelectionProps> = memo(({
  selectedIndices,
  setSelectedIndices,
  onContinue,
  onBack,
  isLastStep
}) => {
  const { availableIndices, loading, error } = useFetchIndices();
  const [searchTerm, setSearchTerm] = useState('');
  const { dispatch } = useUnifiedFilter();

  // Keep selections in local state only
  const [localIndices, setLocalIndices] = useState(selectedIndices);

  // Memoize filtered indices
  const filteredIndices = useMemo(() =>
    availableIndices.filter(index =>
      index.display_name.toLowerCase().includes(searchTerm.toLowerCase())
    ),
    [availableIndices, searchTerm]
  );

  // Create a memoized Set of selected index names for O(1) lookup
  const selectedIndexSet = useMemo(() =>
    new Set(localIndices.map(index => index.name)),
    [localIndices]
  );

  // Compute allSelected based on memoized set
  const allSelected = useMemo(() =>
    availableIndices.length > 0 &&
    selectedIndexSet.size === availableIndices.length &&
    availableIndices.every(index => selectedIndexSet.has(index.name)),
    [availableIndices, selectedIndexSet]
  );

  // Handle local index changes without updating context
  const handleIndexChange = useCallback((index: Index) => {
    setLocalIndices(prevIndices => {
      const isSelected = selectedIndexSet.has(index.name);
      return isSelected
        ? prevIndices.filter(i => i.name !== index.name)
        : [...prevIndices, index];
    });
  }, [selectedIndexSet]);

  // Handle select all without updating context
  const handleSelectAll = useCallback(() => {
    setLocalIndices(prevIndices =>
      prevIndices.length === availableIndices.length ? [] : [...availableIndices]
    );
  }, [availableIndices]);

  // Update context only when continuing to next step
  const handleContinue = useCallback(() => {
    // Update parent state
    setSelectedIndices(localIndices);

    // Update context with all changes at once
    dispatch({
      type: 'SET_UPLOAD_FILTERS',
      payload: { indices: localIndices }
    });

    // Call the original onContinue
    onContinue({ indices: localIndices });
  }, [localIndices, setSelectedIndices, dispatch, onContinue]);

  const handleSearch = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  }, []);

  // Memoized checkbox item to prevent unnecessary re-renders
  const CheckboxItem = memo(({ index }: { index: Index }) => (
    <li className="indices-list-item">
      <label>
        <input
          type="checkbox"
          checked={selectedIndexSet.has(index.name)}
          onChange={() => handleIndexChange(index)}
        />
        {index.display_name}&nbsp;&nbsp;
        <em>{index.role_of_current_user}</em>
      </label>
    </li>
  ));

  CheckboxItem.displayName = 'CheckboxItem';

  if (loading) {
    return <div className="indices-selector-container">Loading indices...</div>;
  }

  return (
    <div className="indices-selector-container">
      {error && <div className="indices-selector-error">{error}</div>}

      <input
        type="text"
        className="indices-search-input"
        placeholder="Search databases..."
        value={searchTerm}
        onChange={handleSearch}
      />

      <div className="select-all-container">
        <label>
          <input
            type="checkbox"
            checked={allSelected}
            onChange={handleSelectAll}
          />
          Select All
        </label>
      </div>

      <div className="indices-list-scrollable">
        <ul className="indices-list">
          {filteredIndices.map((index: Index) => (
            <CheckboxItem key={index.name} index={index} />
          ))}
        </ul>
      </div>

      <div className="navigation-buttons">
        {onBack && <button onClick={onBack}>Back</button>}
        <button onClick={handleContinue}>
          {isLastStep ? 'Complete' : 'Continue'}
        </button>
      </div>
    </div>
  );
});

IndicesSelection.displayName = 'IndicesSelection';

export default IndicesSelection;
