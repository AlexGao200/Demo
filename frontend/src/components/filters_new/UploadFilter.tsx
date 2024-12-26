import React, { useState, useEffect, useCallback, useRef } from 'react';
import BaseFilter, { NavigationCallbacks } from './BaseFilter';
import { FilterStep, FilterProps, Index, FilterStepProps, FilterState } from '../../types/FilterTypes';
import IndicesSelection from './IndicesSelection';
import FilterSelection from './FilterSelection';
import VisibilitySelection from './VisibilitySelection';
import UploadContainer from './UploadContainer';
import { useUnifiedFilter, setUploadFilters } from '../../context/UnifiedFilterContext';
import { useThemeContext } from '../../context/ThemeContext';
import { useVisibilityOptions } from '../../hooks/useVisibilityOptions';

interface UploadFilterProps {
  onComplete: (data: FilterProps) => void;
  onAbort: () => void;
}

const UploadFilter: React.FC<UploadFilterProps> = ({ onComplete, onAbort }) => {
  const { state, dispatch } = useUnifiedFilter();
  const [selectedIndices, setSelectedIndices] = useState<Index[]>(state.upload.indices || []);
  const [filters, setFilters] = useState<FilterState>(state.upload.filters || {});
  const [visibility, setVisibility] = useState<{ [key: string]: string }>(state.upload.visibility || {});
  const [error, setError] = useState<string | null>(null);
  const { theme } = useThemeContext();
  const updateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch visibility options when indices change
  const { loading: loadingVisibilities, error: visibilityError } = useVisibilityOptions(selectedIndices);

  // Determine if visibility selection is needed
  const needsVisibilitySelection = useCallback((indices: Index[]) => {
    return indices.some(index => {
      // If visibility_options_for_user is not yet loaded, assume we need visibility selection
      if (!index.visibility_options_for_user) return true;
      return index.visibility_options_for_user.length > 1;
    });
  }, []);

  const autoSetVisibility = useCallback((indices: Index[]) => {
    const newVisibility = { ...visibility };
    indices.forEach(index => {
      if (index.visibility_options_for_user?.length === 1) {
        newVisibility[index.name] = index.visibility_options_for_user[0];
      }
    });
    setVisibility(newVisibility);
    return newVisibility;
  }, [visibility]);

  // Debounced update to UnifiedFilterContext
  useEffect(() => {
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
    }

    updateTimeoutRef.current = setTimeout(() => {
      try {
        const currentState = {
          indices: selectedIndices,
          filters,
          visibility
        };

        // Only update if the state has actually changed
        if (JSON.stringify(currentState) !== JSON.stringify({
          indices: state.upload.indices,
          filters: state.upload.filters,
          visibility: state.upload.visibility
        })) {
          setUploadFilters(dispatch, currentState);
        }
      } catch (err) {
        console.error('Error updating filters in UnifiedFilterContext:', err);
        setError('Failed to update filters. Please try again.');
      }
    }, 300); // Debounce for 300ms

    return () => {
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }
    };
  }, [selectedIndices, filters, visibility, dispatch, state.upload]);

  const handleComplete = (data: FilterProps) => {
    try {
      setUploadFilters(dispatch, { uploadResult: data.uploadResult });
      onComplete(data);
    } catch (err) {
      console.error('Error completing upload:', err);
      setError('Failed to complete upload. Please try again.');
    }
  };

  const handleIndicesChange = useCallback((indices: Index[]) => {
    console.log('Indices changed:', indices);
    setSelectedIndices(indices);
    autoSetVisibility(indices);
  }, [autoSetVisibility]);

  // Dynamically build steps based on whether visibility selection is needed
  const getUploadSteps = useCallback((): FilterStep[] => {
    const baseSteps: FilterStep[] = [
      {
        name: 'indices',
        title: 'Select Databases',
        component: ({ onContinue, onBack, isLastStep }: FilterStepProps & NavigationCallbacks) => (
          <IndicesSelection
            onContinue={(data) => {
              handleIndicesChange(data.indices || []);
              onContinue(data);
            }}
            onBack={onBack}
            isLastStep={isLastStep}
            selectedIndices={selectedIndices}
            setSelectedIndices={setSelectedIndices}
          />
        ),
      },
      {
        name: 'filter',
        title: 'Apply Filters',
        component: ({ onContinue, onBack, isLastStep }: FilterStepProps & NavigationCallbacks) => (
          <FilterSelection
            selectedIndices={selectedIndices}
            onContinue={(data) => {
              console.log('FilterSelection onContinue:', data);
              setFilters(data.filters || {});
              onContinue(data);
            }}
            onBack={onBack}
            isLastStep={isLastStep}
            initialFilters={filters}
            theme={theme}
            requireChoice={true}
            canAddFilterDims={true}
          />
        ),
      }
    ];

    // Only add visibility step if any selected indices have multiple visibility options
    // and visibility options have been loaded
    if (!loadingVisibilities && needsVisibilitySelection(selectedIndices)) {
      baseSteps.push({
        name: 'visibility',
        title: 'Set Visibility',
        component: ({ onContinue, onBack, isLastStep }: FilterStepProps & NavigationCallbacks) => (
          <VisibilitySelection
            selectedIndices={selectedIndices}
            onContinue={(data) => {
              setVisibility(data.visibility || {});
              onContinue(data);
            }}
            onBack={onBack}
            isLastStep={isLastStep}
          />
        ),
      });
    }

    // Add upload step
    baseSteps.push({
      name: 'upload',
      title: 'Upload Files',
      component: ({ onContinue, onBack, isLastStep }: FilterStepProps & NavigationCallbacks) => (
        <UploadContainer
          selectedIndices={selectedIndices}
          filters={filters}
          visibility={visibility}
          creatorOrgDisplayName={selectedIndices[0]?.display_name || ''}
          onContinue={onContinue}
          onBack={onBack}
          isLastStep={isLastStep}
        />
      ),
    });

    return baseSteps;
  }, [selectedIndices, filters, visibility, theme, handleIndicesChange, needsVisibilitySelection, loadingVisibilities]);

  const renderStep = (stepProps: FilterStepProps & NavigationCallbacks, step: FilterStep) => {
    const StepComponent = step.component;
    return <StepComponent {...stepProps} />;
  };

  return (
    <div>
      {(error || visibilityError) && (
        <div className="error-message">{error || visibilityError}</div>
      )}
      {loadingVisibilities && <div>Loading visibility options...</div>}
      <BaseFilter
        steps={getUploadSteps()}
        renderStep={renderStep}
        onComplete={handleComplete}
        onAbort={onAbort}
      />
    </div>
  );
};

export default UploadFilter;
