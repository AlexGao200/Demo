import { useState, useEffect, useRef } from 'react';
import { Index } from '../types/FilterTypes';
import axiosInstance from '../axiosInstance';
import { useUserContext } from '../context/UserContext';
import { useUnifiedFilter, setAvailableIndices, setUploadFilters } from '../context/UnifiedFilterContext';

interface IndexResponse {
  display_name: string;
  visibility_options_for_user: string[];
  name: string;
  role_of_current_user: string;
}

interface VisibilityMap {
  [key: string]: string;
}

export const useFetchIndices = () => {
  const { user, guestToken } = useUserContext();
  const { state, dispatch } = useUnifiedFilter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fetchInProgressRef = useRef(false);
  const initialFetchDoneRef = useRef(false);

  useEffect(() => {
    const fetchIndices = async () => {
      // Skip if already fetching or have indices and initial fetch is done
      if (fetchInProgressRef.current ||
          (state.availableIndices.length > 0 && initialFetchDoneRef.current)) {
        return;
      }

      fetchInProgressRef.current = true;

      try {
        setLoading(true);
        setError(null);

        // Use unified endpoint for both user and guest sessions
        const response = await axiosInstance.get<{ indices: IndexResponse[] }>('/user/indices');

        if (!response.data.indices || !Array.isArray(response.data.indices)) {
          throw new Error('Invalid response format');
        }

        const transformedIndices = response.data.indices.map(index => ({
          ...index,
          id: index.name
        }));

        const initialVisibility: VisibilityMap = {};
        transformedIndices.forEach(index => {
          if (index.visibility_options_for_user?.length > 0) {
            initialVisibility[index.name] = index.visibility_options_for_user[0];
          }
        });

        // Only update context if the indices have changed
        if (JSON.stringify(transformedIndices) !== JSON.stringify(state.availableIndices)) {
          setAvailableIndices(dispatch, transformedIndices);
          setUploadFilters(dispatch, { visibility: initialVisibility });
        }

        initialFetchDoneRef.current = true;
      } catch (err: any) {
        console.error('[useFetchIndices] Error fetching indices:', err);
        setError(err.message || 'Failed to fetch indices');
      } finally {
        setLoading(false);
        fetchInProgressRef.current = false;
      }
    };

    fetchIndices();
  }, [user?.id, guestToken, dispatch]); // Keep dependencies to track session changes

  const refetch = () => {
    initialFetchDoneRef.current = false;
    fetchInProgressRef.current = false;
    setAvailableIndices(dispatch, []);
  };

  return {
    availableIndices: state.availableIndices,
    loading,
    error,
    refetch
  };
};
