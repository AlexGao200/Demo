import React, { useMemo, useCallback } from 'react';
import { Index } from '../../types/FilterTypes';
import { NavigationCallbacks } from './BaseFilter';
import { useUnifiedFilter, setUploadFilters } from '../../context/UnifiedFilterContext';
import '../../styles/VisibilitySelection.css';

interface VisibilitySelectionProps extends NavigationCallbacks {
  selectedIndices: Index[];
}

const VisibilitySelection: React.FC<VisibilitySelectionProps> = ({ onContinue, onBack, isLastStep, selectedIndices }) => {
  const { state, dispatch } = useUnifiedFilter();

  const visibility = useMemo(() => {
    const currentVisibility = state.upload.visibility || {};
    const updatedVisibility = { ...currentVisibility };
    selectedIndices.forEach(index => {
      if (!updatedVisibility[index.name] && index.visibility_options_for_user.length > 0) {
        // Default to first available visibility option
        updatedVisibility[index.name] = index.visibility_options_for_user[0] as 'public' | 'private';
      }
    });
    return updatedVisibility;
  }, [state.upload.visibility, selectedIndices]);

  const handleVisibilityChange = useCallback((indexName: string, value: 'public' | 'private') => {
    const updatedVisibility = { ...visibility, [indexName]: value };
    setUploadFilters(dispatch, { visibility: updatedVisibility });
  }, [visibility, dispatch]);

  const handleSubmit = useCallback(() => {
    onContinue({ visibility });
  }, [onContinue, visibility]);

  return (
    <div className="visibility-selector-container">
      <ul className="visibility-list">
        {selectedIndices.map(index => (
          <li key={index.name} className="visibility-list-item">
            <label htmlFor={`visibility-${index.name}`}>{index.display_name}</label>
            <select
              id={`visibility-${index.name}`}
              className="visibility-select"
              value={visibility[index.name] || index.visibility_options_for_user[0]}
              onChange={(e) => handleVisibilityChange(index.name, e.target.value as 'public' | 'private')}
            >
              {index.visibility_options_for_user.map(option => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
      <div className="navigation-buttons">
        {onBack && <button onClick={onBack}>Back</button>}
        <button onClick={handleSubmit}>{isLastStep ? 'Complete' : 'Continue'}</button>
      </div>
    </div>
  );
};

export default VisibilitySelection;
