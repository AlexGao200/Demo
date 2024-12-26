import { useState, useCallback } from 'react';
import axiosInstance from '../axiosInstance';
import { ApiError, handleApiError } from '../utils/errorHandling';

interface UseApiResult<T, R> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  execute: (data?: R) => Promise<void>;
}

export function useApi<T, R = unknown>(
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET'
): UseApiResult<T, R> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  const execute = useCallback(async (requestData?: R) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axiosInstance({
        method,
        url: endpoint,
        data: method !== 'GET' ? requestData : undefined,
        params: method === 'GET' ? requestData : undefined,
      });

      setData(response.data);
    } catch (error: unknown) {
      setError(handleApiError(error));
    } finally {
      setLoading(false);
    }
  }, [endpoint, method]);

  return { data, loading, error, execute };
}
