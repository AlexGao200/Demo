import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { debounce } from 'lodash';
import axiosInstance from '../../axiosInstance';
import { Index, FilterState } from '../../types/FilterTypes';
import { NavigationCallbacks } from './BaseFilter';
import FilterModal from './FilterModal';
import { useCreateFilterDimension } from '../../hooks/useCreateFilterDimension';
import '../../styles/FilterSelection.css';
import { FixedSizeList as List } from 'react-window';

interface FilterSelectionProps extends NavigationCallbacks {
  selectedIndices: Index[];
  initialFilters?: FilterState;
  theme: 'light' | 'dark';
  requireChoice: boolean;
  canAddFilterDims: boolean;
}

interface FilterDimension {
  id: string;
  name: string;
  values: string[];
}

interface FilterResponse {
  filter_dimensions: FilterDimension[];
}

interface FilterItemProps {
  index: number;
  style: React.CSSProperties;
}

const ITEMS_PER_PAGE = 10;
const MIN_FILTER_LENGTH = 3;

const FilterSelection: React.FC<FilterSelectionProps> = ({
  selectedIndices,
  onContinue,
  onBack,
  isLastStep,
  initialFilters,
  theme,
  requireChoice,
  canAddFilterDims,
}) => {
  const [availableFilters, setAvailableFilters] = useState<FilterDimension[]>([]);
  const [selectedFilters, setSelectedFilters] = useState<FilterState>(initialFilters || {});
  const [tempSelectedFilters, setTempSelectedFilters] = useState<FilterState>({});
  const [unselectedList, setUnselectedList] = useState<FilterDimension[]>([]);
  const [selectedList, setSelectedList] = useState<FilterDimension[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [selectedDimension, setSelectedDimension] = useState<FilterDimension | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [filterValuesLoading, setFilterValuesLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddDimensionModal, setShowAddDimensionModal] = useState(false);
  const [newDimensionName, setNewDimensionName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { createFilterDimension, loading: creatingDimension } = useCreateFilterDimension();

  // Memoize the fetch filters function
  const fetchFilters = useCallback(async () => {
    if (selectedIndices.length === 0) {
      setError('No indices selected. Please go back and select at least one index.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await axiosInstance.get<FilterResponse>('/filter/get-filter-dimensions', {
        params: {
          'index_names[]': selectedIndices.map((index) => index.name),
          page: currentPage,
          limit: ITEMS_PER_PAGE,
        },
      });

      const newFilters = response.data.filter_dimensions || [];

      setAvailableFilters((prevFilters) => {
        const filterSet = new Set(prevFilters.map((f) => f.id));
        const uniqueNewFilters = newFilters.filter((newFilter: FilterDimension) => !filterSet.has(newFilter.id));
        return [...prevFilters, ...uniqueNewFilters];
      });

      setUnselectedList((prevList) => {
        const filterSet = new Set(prevList.map((f) => f.id));
        const uniqueNewFilters = newFilters.filter((newFilter: FilterDimension) => !filterSet.has(newFilter.id));
        return [...prevList, ...uniqueNewFilters];
      });

      setHasMore(newFilters.length === ITEMS_PER_PAGE);
      setLoading(false);
    } catch (err) {
      setError('Failed to fetch filters. Please try again later.');
      console.error('Error fetching filters:', err);
      setLoading(false);
    }
  }, [selectedIndices, currentPage]);

  useEffect(() => {
    fetchFilters();
  }, [fetchFilters]);

  useEffect(() => {
    if (initialFilters) {
      setSelectedFilters(initialFilters);

      const selectedDimensions = availableFilters.filter(filter =>
        initialFilters[filter.id]?.values?.length > 0
      );
      const unselectedDimensions = availableFilters.filter(filter =>
        !initialFilters[filter.id]?.values?.length
      );

      setSelectedList(selectedDimensions);
      setUnselectedList(unselectedDimensions);
    }
  }, [initialFilters, availableFilters]);

  const handleFilterChange = useMemo(
    () =>
      debounce((filterId: string, values: string[]) => {
        setTempSelectedFilters(prev => ({
          ...prev,
          [filterId]: { values },
        }));
      }, 200),
    []
  );

  const handleComplete = useCallback(() => {
    if (requireChoice && selectedList.length === 0) {
      setError('Please select at least one filter for upload.');
      return;
    }
    setIsSubmitting(true);

    const processedFilters = selectedList.reduce((acc, filter) => {
      const filterId = filter.id;
      const selectedFilter = selectedFilters[filterId] || { values: [] };
      acc[filterId] = Array.isArray(selectedFilter.values)
        ? selectedFilter.values
        : [selectedFilter.values];
      return acc;
    }, {} as Record<string, string[]>);

    onContinue({ filters: processedFilters });
    setIsSubmitting(false);
  }, [selectedList, selectedFilters, requireChoice, onContinue]);

  const handleDimensionClick = useCallback((dimension: FilterDimension) => {
    const isAlreadySelected = selectedList.some((filter) => filter.id === dimension.id);

    if (isAlreadySelected) {
      setSelectedList(prev => prev.filter(filter => filter.id !== dimension.id));
      setUnselectedList(prev => [...prev, dimension]);
    } else {
      setUnselectedList(prev => prev.filter(filter => filter.id !== dimension.id));
      setSelectedList(prev => [...prev, dimension]);
      setSelectedDimension(dimension);
      setShowModal(true);
    }
  }, [selectedList]);

  const handleConfirm = useCallback(() => {
    if (selectedDimension?.id) {
      setSelectedFilters(prev => ({
        ...prev,
        [selectedDimension.id]: tempSelectedFilters[selectedDimension.id] || { values: [] },
      }));
    }
    setShowModal(false);
    setSelectedDimension(null);
    setTempSelectedFilters({});
  }, [selectedDimension, tempSelectedFilters]);

  const handleModalClose = useCallback(() => {
    setShowModal(false);
    setSelectedDimension(null);
    setTempSelectedFilters({});
  }, []);

  const handleCreateNewValue = useCallback(async (newValue: string) => {
    if (!selectedDimension || newValue.trim().length < MIN_FILTER_LENGTH) {
      setError(`Filter value must be at least ${MIN_FILTER_LENGTH} characters long.`);
      return;
    }

    try {
      await axiosInstance.post('/filter/add-value-to-filter-dimension', {
        dimension_id: selectedDimension.id,
        value: newValue.trim(),
      });

      setSelectedDimension(prev => {
        if (!prev) return null;
        return {
          ...prev,
          values: [...prev.values, newValue.trim()]
        };
      });
    } catch (err) {
      console.error('Error creating new filter value:', err);
      setError('Failed to create new filter value. Please try again.');
    }
  }, [selectedDimension]);

  const handleAddFilterDimension = useCallback(async () => {
    if (newDimensionName.trim().length < MIN_FILTER_LENGTH) {
      setError(`Filter category name must be at least ${MIN_FILTER_LENGTH} characters long.`);
      return;
    }

    try {
      await createFilterDimension(newDimensionName.trim(), selectedIndices.map(index => index.name));
      setNewDimensionName('');
      setShowAddDimensionModal(false);
      fetchFilters();
    } catch (err) {
      console.error('Error creating new filter category:', err);
      setError('Failed to create new filter category. Please try again.');
    }
  }, [newDimensionName, createFilterDimension, selectedIndices, fetchFilters]);

  const filteredFilters = useMemo(() => {
    const combined = [...selectedList, ...unselectedList];
    return combined.filter(filter =>
      filter.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [selectedList, unselectedList, searchTerm]);

  // Define FilterItem as a proper React component
  const FilterItem = React.memo<FilterItemProps>(({ index, style }) => {
    const filter = filteredFilters[index];
    const isSelected = selectedList.some((f) => f.id === filter.id);

    return (
      <div style={style} className="filter-list-item">
        <button
          className={`filter-select-button ${isSelected ? 'selected-filter-button' : ''}`}
          onClick={() => handleDimensionClick(filter)}
        >
          {filter.name}
        </button>
      </div>
    );
  });

  FilterItem.displayName = 'FilterItem';

  if (loading && currentPage === 1) {
    return <div className="filter-selector-container" aria-live="polite">Loading filters...</div>;
  }

  if (error) {
    return (
      <div className="filter-selector-container" aria-live="assertive">
        <p>Error: {error}</p>
        <button className="filter-select-button" onClick={onBack}>
          Back
        </button>
      </div>
    );
  }

  return (
    <div className={`filter-selector-container ${theme}-theme`}>
      {error && <div className="error-message" role="alert">{error}</div>}

      {canAddFilterDims && (
        <button className="add-filter-button" onClick={() => setShowAddDimensionModal(true)}>
          Add Filter Category
        </button>
      )}

      <input
        type="text"
        className="filter-search-input"
        placeholder="Search filters..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        aria-label="Search filters"
      />

      <div className="filter-list-scrollable">
        <List
          height={400}
          itemCount={filteredFilters.length}
          itemSize={35}
          width="100%"
        >
          {FilterItem}
        </List>
        {loading && <div>Loading more filter categories...</div>}
      </div>

      <div className="navigation-buttons">
        {onBack && <button className="add-filter-button" onClick={onBack}>Back</button>}
        <button
          className="done-button"
          onClick={handleComplete}
          disabled={isSubmitting || (requireChoice && selectedList.length === 0)}
        >
          {isSubmitting ? 'Submitting...' : isLastStep ? 'Complete' : 'Continue'}
        </button>
      </div>

      {showModal && selectedDimension && (
        <FilterModal
          title={`Select values for ${selectedDimension.name}`}
          onAbort={handleModalClose}
        >
          {filterValuesLoading ? (
            <div aria-live="polite">Loading filter values...</div>
          ) : (
            <div>
              <input
                type="text"
                className="filter-search-input"
                placeholder="Search values..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <div className="filter-values-list-scrollable">
                {selectedDimension.values.map((value) => {
                  const isSelected = (tempSelectedFilters[selectedDimension.id]?.values || []).includes(value);
                  return (
                    <button
                      key={value}
                      className={`filter-select-button ${isSelected ? 'selected-filter-button' : ''}`}
                      onClick={() => {
                        const newValues = isSelected
                          ? (tempSelectedFilters[selectedDimension.id]?.values || []).filter((v: string) => v !== value)
                          : [...(tempSelectedFilters[selectedDimension.id]?.values || []), value];
                        handleFilterChange(selectedDimension.id, newValues);
                      }}
                    >
                      {value}
                    </button>
                  );
                })}
              </div>
              <div className="modal-actions">
                <input
                  type="text"
                  id="newValue"
                  placeholder="New value"
                  aria-label="New filter value"
                  className="filter-search-input"
                />
                <button
                  className="add-filter-button"
                  onClick={() => {
                    const newValue = (document.getElementById('newValue') as HTMLInputElement).value;
                    handleCreateNewValue(newValue);
                  }}
                >
                  Create New Value
                </button>
                <button className="add-filter-button" onClick={handleModalClose}>
                  Cancel
                </button>
                <button className="done-button" onClick={handleConfirm}>
                  Confirm
                </button>
              </div>
            </div>
          )}
        </FilterModal>
      )}

      {showAddDimensionModal && (
        <FilterModal
          title="Add Filter Category"
          onAbort={() => setShowAddDimensionModal(false)}
        >
          <div>
            <input
              type="text"
              value={newDimensionName}
              onChange={(e) => setNewDimensionName(e.target.value)}
              placeholder="Enter new filter category name"
              className="filter-search-input"
              aria-label="New filter category name"
            />
            <div className="modal-actions">
              <button
                className="add-filter-button"
                onClick={() => setShowAddDimensionModal(false)}
              >
                Cancel
              </button>
              <button
                className="done-button"
                onClick={handleAddFilterDimension}
                disabled={creatingDimension || newDimensionName.trim().length < MIN_FILTER_LENGTH}
              >
                {creatingDimension ? 'Adding...' : 'Add'}
              </button>
            </div>
          </div>
        </FilterModal>
      )}
    </div>
  );
};

export default React.memo(FilterSelection);
