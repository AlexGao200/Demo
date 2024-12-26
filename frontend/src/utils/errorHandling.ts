import { AxiosError } from 'axios';

export interface ApiError {
  message: string;
  details?: string;
}

export function handleApiError(error: unknown): ApiError {
  const apiError: ApiError = { message: 'An unexpected error occurred' };

  if (error instanceof AxiosError) {
    apiError.message = error.response?.data?.message || error.message;
    apiError.details = error.response?.data?.details || error.toString();
  } else if (error instanceof Error) {
    apiError.message = error.message;
    apiError.details = error.stack;
  }

  console.error('API Error:', apiError);
  return apiError;
}
