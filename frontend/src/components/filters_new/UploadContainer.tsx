import React, { useState, useCallback, useEffect } from 'react';
import axiosInstance from '../../axiosInstance';
import { FilterProps, Index } from '../../types/FilterTypes';
import { NavigationCallbacks } from './BaseFilter';

interface UploadContainerProps extends NavigationCallbacks {
  selectedIndices: Index[];
  filters: FilterProps['filters'];
  visibility: { [key: string]: string};
  creatorOrgDisplayName?: string; // Make this optional
}

interface FilterInfo {
  id: string;
  name: string;
}

const UploadContainer: React.FC<UploadContainerProps> = ({
  selectedIndices,
  filters,
  visibility,
  creatorOrgDisplayName,
  onContinue,
  onBack,
  isLastStep,
}) => {
  const [files, setFiles] = useState<File[]>([]);
  const [titles, setTitles] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterDetails, setFilterDetails] = useState<FilterInfo[]>([]); // Holds fetched filter names

  // Fallback for creatorOrgDisplayName if undefined
  const resolvedCreatorOrgDisplayName = creatorOrgDisplayName || selectedIndices[0]?.display_name || 'Unknown';

  // Log the creatorOrgDisplayName for debugging
  useEffect(() => {
    console.log('Resolved Creator Org Display Name:', resolvedCreatorOrgDisplayName);
  }, [resolvedCreatorOrgDisplayName]);

  // Log the initial filters and filter details for debugging
  useEffect(() => {
    console.log("Initial filters object:", filters);
    console.log("Initial filter details array:", filterDetails);
  }, [filters, filterDetails]);

  // Fetch filter names (dimension names) using filter IDs
  const fetchFilterDetails = useCallback(async () => {
    const filterIds = Object.keys(filters); // Extract filter object IDs from the filters object

    console.log("Fetching filter details for filterIds:", filterIds);

    if (filterIds.length === 0) {
      console.warn("No filter IDs available.");
      return;
    }

    try {
      const response = await axiosInstance.post('/filter/get-filter-names-values', {
        filterIds, // Send the filter IDs to the backend
      });

      if (response.status === 200) {
        console.log("Fetched filter details from backend:", response.data.filters);
        setFilterDetails(response.data.filters.map((filter: any) => ({
          id: filter.id,
          name: filter.name,
        })));
      } else {
        setError('Failed to retrieve filter details.');
      }
    } catch (err) {
      setError('Error fetching filter details.');
      console.error('Fetch filter details error:', err);
    }
  }, [filters]);

  // Run the fetch function when the component mounts or when filters change
  useEffect(() => {
    fetchFilterDetails();
  }, [fetchFilterDetails]);

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const newFiles = Array.from(event.target.files);
      const newTitles = newFiles.map(file => file.name);

      setFiles(prevFiles => [...prevFiles, ...newFiles]);
      setTitles(prevTitles => [...prevTitles, ...newTitles]);
    }
  }, []);

  const handleTitleChange = useCallback((index: number, value: string) => {
    setTitles(prevTitles => {
      const newTitles = [...prevTitles];
      newTitles[index] = value;
      return newTitles;
    });
  }, []);

  const handleUpload = useCallback(async () => {
    if (files.length === 0) {
      setError('No files selected');
      return;
    }

    if (titles.some(title => title.trim() === '')) {
      setError('All files must have a title');
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    files.forEach((file, index) => {
      formData.append('files', file);
      formData.append('titles', titles[index]);
    });

    formData.append('index_names', selectedIndices.map(index => index.name).join(','));
    formData.append('file_visibilities', JSON.stringify(visibility));
    formData.append('filter_dimensions', JSON.stringify(filters));
    formData.append('nominal_creator_name', resolvedCreatorOrgDisplayName);

    try {
      const response = await axiosInstance.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.status === 200) {
        onContinue({ uploadResult: response.data });
      } else {
        setError('Upload failed. Please try again.');
      }
    } catch (err) {
      setError('An error occurred during upload.');
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  }, [files, titles, selectedIndices, visibility, filters, resolvedCreatorOrgDisplayName, onContinue]);

  // Function to render selected filter values based on the filters object
  const renderSelectedFilters = () => {
    const renderedFilters = filterDetails
      .map(detail => {
        const selectedValues = filters[detail.id];  // Correctly access the values from the filters object

        if (selectedValues && selectedValues.length > 0) {
          console.log(`Filter detail for ${detail.name}: Selected values =`, selectedValues);
          return `${detail.name}: ${selectedValues.join(', ')}`;
        }
        return null; // Skip filters that have no selected values
      })
      .filter(Boolean) // Remove null values
      .join(', ');

    console.log("Rendered filters:", renderedFilters);
    return renderedFilters;
  };

  return (
    <div className="upload-container">
      <h3>Selected Databases:</h3>
      {selectedIndices.length === 0 ? (
        <p>No indices selected</p>
      ) : (
        <p>{selectedIndices.map(index => index.display_name).join(', ')}</p>
      )}

      <h3>Selected Categories:</h3>
      {filterDetails.length === 0 ? (
        <p>No filters applied</p>
      ) : (
        <p>{renderSelectedFilters()}</p>  // Render the selected filter values
      )}

      {/* Display the visibility */}
      <h3>File Visibility:</h3>
      {Object.values(visibility).length > 0 ? (
        <p>Visibility: {Object.values(visibility)[0]}</p>
      ) : (
        <p>Visibility: Not specified</p>
      )}

      <input type="file" multiple onChange={handleFileChange} accept=".pdf,.doc,.docx,.txt" />
      {files.map((file, index) => (
        <div key={index} className="file-item">
          <input
            type="text"
            value={titles[index]}
            onChange={(e) => handleTitleChange(index, e.target.value)}
            placeholder="Enter file title"
          />
          <span>{file.name}</span>
        </div>
      ))}

      <div className="navigation-buttons">
        {onBack && <button onClick={onBack}>Back</button>}
        <button onClick={handleUpload} disabled={uploading}>
          {uploading ? 'Uploading...' : isLastStep ? 'Complete' : 'Continue'}
        </button>
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  );
};

export default UploadContainer;
