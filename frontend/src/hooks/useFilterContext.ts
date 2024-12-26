import { useState, useCallback, useRef } from 'react';

export type FilterDimension = {
  name: string;
  selectionType: 'single' | 'multi';
  dataType: 'string' | 'number' | 'date';
  values: string[];
};

export type FilterState = {
  [key: string]: string[];
};

export function useFilterContext(initialDimensions: FilterDimension[]) {
  const [dimensions, setDimensions] = useState<FilterDimension[]>(initialDimensions);
  const [filterState, setFilterState] = useState<FilterState>({});
  const dimensionsRef = useRef(dimensions);

  // Update dimensions reference when dimensions change
  const updateDimensions = useCallback((newDimensions: FilterDimension[]) => {
    setDimensions(newDimensions);
    dimensionsRef.current = newDimensions;
  }, []);

  const updateFilter = useCallback((dimensionName: string, value: string | string[]) => {
    setFilterState(prevState => {
      const dimension = dimensionsRef.current.find(d => d.name === dimensionName);
      if (!dimension) return prevState;

      const newValues = Array.isArray(value) ? value : [value];

      if (dimension.selectionType === 'single') {
        return {
          ...prevState,
          [dimensionName]: newValues.slice(-1) // Only keep the last value for single select
        };
      } else {
        // For multi-select, we'll toggle the values
        const currentValues = prevState[dimensionName] || [];
        const updatedValues = newValues.reduce((acc, val) => {
          if (currentValues.includes(val)) {
            return acc.filter(v => v !== val);
          } else {
            return [...acc, val];
          }
        }, currentValues);

        return {
          ...prevState,
          [dimensionName]: updatedValues
        };
      }
    });
  }, []);

  const resetFilter = useCallback((dimensionName: string) => {
    setFilterState(prevState => {
      const newState = { ...prevState };
      delete newState[dimensionName];
      return newState;
    });
  }, []);

  const clearAllFilters = useCallback(() => {
    setFilterState({});
  }, []);

  return {
    dimensions,
    filterState,
    updateFilter,
    resetFilter,
    clearAllFilters,
    updateDimensions
  };
}
