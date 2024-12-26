import React, { useCallback, useState } from 'react';
import BaseFilter, { NavigationCallbacks } from './BaseFilter';
import { FilterStep, Index, FilterProps, FilterStepProps } from '../../types/FilterTypes';
import IndicesSelection from './IndicesSelection';
import FilterSelection from './FilterSelection';
import { useUnifiedFilter, setQueryFilters } from '../../context/UnifiedFilterContext';
import { useThemeContext } from '../../context/ThemeContext';

const QueryFilter: React.FC<{ onComplete: (data: FilterProps) => void; onAbort: () => void }> = ({ onComplete, onAbort }) => {
  const { dispatch } = useUnifiedFilter();
  const [selectedIndices, setSelectedIndices] = useState<Index[]>([]);
  const { theme } = useThemeContext();

  // Instead of updating context immediately, we'll collect all changes
  const [filterData, setFilterData] = useState<Partial<FilterProps>>({});

  const handleIndicesChange = useCallback((indices: Index[]) => {
    setSelectedIndices(indices);
    setFilterData(prev => ({ ...prev, indices }));
  }, []);

  const handleFiltersChange = useCallback((filters: FilterProps['filters']) => {
    setFilterData(prev => ({ ...prev, filters }));
  }, []);

  // Only update context and trigger fetch when the entire filter process is complete
  const handleComplete = useCallback((data: FilterProps) => {
    setQueryFilters(dispatch, data);
    onComplete(data);
  }, [dispatch, onComplete]);

  const querySteps: FilterStep[] = [
    {
      name: 'indices',
      title: 'Select Databases',
      component: ({ onContinue, onBack, isLastStep }: FilterStepProps & NavigationCallbacks) => (
        <IndicesSelection
          onContinue={(data: Partial<FilterProps>) => {
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
      component: ({ onContinue, onBack, isLastStep, filterData }: FilterStepProps & NavigationCallbacks) => (
        <FilterSelection
          selectedIndices={selectedIndices}
          onContinue={(data: Partial<FilterProps>) => {
            handleFiltersChange(data.filters || {});
            onContinue(data);
          }}
          onBack={onBack}
          isLastStep={isLastStep}
          initialFilters={filterData.filters}
          theme={theme}
          requireChoice={false}
          canAddFilterDims={false}
        />
      ),
    },
  ];

  const renderStep = (stepProps: FilterStepProps & NavigationCallbacks, step: FilterStep) => {
    const StepComponent = step.component;
    return <StepComponent {...stepProps} />;
  };

  return <BaseFilter
    steps={querySteps}
    renderStep={renderStep}
    onComplete={handleComplete}
    onAbort={onAbort}
  />;
};

export default QueryFilter;
