import React, { useState, useContext, useCallback, useMemo } from 'react';
import { FilterStep, FilterProps, FilterStepProps } from '../../types/FilterTypes';
import FilterModal from './FilterModal';
import { ThemeContext } from '../../context/ThemeContext';
import { ThemeContextType } from '../../types';
import '../../styles/FilterStyles.css';

interface BaseFilterProps {
  steps: FilterStep[];
  renderStep: (stepProps: FilterStepProps, step: FilterStep) => React.ReactNode;
  onComplete: (data: FilterProps) => void;
  onAbort: () => void;
}

export interface NavigationCallbacks {
  onContinue: (stepData: Partial<FilterProps>) => void;
  onBack?: () => void;
  isLastStep: boolean;
}

export const NavigationButtons: React.FC<NavigationCallbacks> = React.memo(({
  onContinue,
  onBack,
  isLastStep
}) => (
  <div className="navigation-buttons">
    {onBack && (
      <button className="nav-back-button" onClick={onBack}>
        Back
      </button>
    )}
    <button className="nav-continue-button" onClick={() => onContinue({})}>
      {isLastStep ? 'Complete' : 'Continue'}
    </button>
  </div>
));

NavigationButtons.displayName = 'NavigationButtons';

const BaseFilter: React.FC<BaseFilterProps> = ({
  steps,
  renderStep,
  onComplete,
  onAbort
}) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [filterData, setFilterData] = useState<FilterProps>({
    indices: [],
    filters: {},
    visibility: {},
    uploadResult: undefined
  });
  const { theme } = useContext(ThemeContext) as ThemeContextType;

  // Memoize current step
  const currentStep = useMemo(() => steps[currentStepIndex], [steps, currentStepIndex]);

  // Memoize navigation state
  const isLastStep = useMemo(() =>
    currentStepIndex === steps.length - 1,
    [currentStepIndex, steps.length]
  );

  // Batch state updates to reduce re-renders
  const handleContinue = useCallback((stepData: Partial<FilterProps>) => {
    // Batch updates using a single setState call
    setFilterData(prev => {
      const updated = { ...prev };
      Object.entries(stepData).forEach(([key, value]) => {
        if (value !== undefined && value !== prev[key as keyof FilterProps]) {
          updated[key as keyof FilterProps] = value;
        }
      });

      // If this is the last step, trigger onComplete
      if (currentStepIndex === steps.length - 1) {
        onComplete(updated);
      }

      return updated;
    });

    // Only update step index if not on last step
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    }
  }, [currentStepIndex, steps.length, onComplete]);

  const handleBack = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  }, [currentStepIndex]);

  // Memoize navigation callbacks
  const navigationCallbacks = useMemo<NavigationCallbacks>(() => ({
    onContinue: handleContinue,
    onBack: currentStepIndex > 0 ? handleBack : undefined,
    isLastStep
  }), [handleContinue, handleBack, currentStepIndex, isLastStep]);

  // Memoize step props
  const stepProps = useMemo(() => ({
    ...navigationCallbacks,
    filterData
  }), [navigationCallbacks, filterData]);

  return (
    <div className={`base-filter filter-container ${theme}-theme`}>
      <FilterModal
        title={currentStep.title}
        onAbort={onAbort}
      >
        <div className="filter-form">
          {renderStep(stepProps, currentStep)}
        </div>
      </FilterModal>
    </div>
  );
};

export default React.memo(BaseFilter);
