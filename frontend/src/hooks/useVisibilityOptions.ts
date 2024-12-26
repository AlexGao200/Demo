import { useState, useEffect } from 'react';
import axios from '../axiosInstance';
import { Index } from '../types/FilterTypes';

export const useVisibilityOptions = (selectedIndices: Index[]) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVisibilityOptions = async () => {
      if (!selectedIndices.length) return;

      setLoading(true);
      setError(null);

      try {
        // Log the request details for debugging
        console.log('Sending request to get visibilities with indices:', selectedIndices.map(index => index.name));

        const response = await axios.post('/filter/get-visibilities', {
          indexNames: selectedIndices.map(index => index.name)
        });

        console.log('Received visibility response:', response.data);

        // Update each index with its visibility options
        const visibilities = response.data.visibilities;
        selectedIndices.forEach(index => {
          index.visibility_options_for_user = visibilities;
        });

      } catch (err) {
        console.error('Error fetching visibility options:', err);
        setError('Failed to fetch visibility options');
      } finally {
        setLoading(false);
      }
    };

    fetchVisibilityOptions();
  }, [selectedIndices]);

  return { loading, error };
};
