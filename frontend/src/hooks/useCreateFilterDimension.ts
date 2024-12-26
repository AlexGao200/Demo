import { useState } from 'react';
import axiosInstance from '../axiosInstance';

interface CreateFilterDimensionResponse {
  message: string;
  dimension_id: string;
  dimension_name: string;
}

export const useCreateFilterDimension = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createFilterDimension = async (dimensionName: string, indexNames: string[]) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axiosInstance.post<CreateFilterDimensionResponse>('/filter/create-filter-dimension', {
        dimension_name: dimensionName,
        index_names: indexNames,
      });

      setLoading(false);
      return response.data;
    } catch (err) {
      setLoading(false);
      setError('Failed to create filter category.');
      throw err;
    }
  };

  return { createFilterDimension, loading, error };
};
