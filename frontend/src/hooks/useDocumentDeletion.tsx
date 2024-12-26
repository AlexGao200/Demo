import { useCallback, useState } from 'react';
import axiosInstance from '../axiosInstance';
import { AxiosError } from 'axios';
import { Document } from '../types';

interface DeleteResult {
  success: boolean;
  error?: string;
  cancelled?: boolean;
  partialSuccess?: boolean;
}

const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

const useDocumentDeletion = (fetchDocuments: () => Promise<void>) => {
  const [isDeleting, setIsDeleting] = useState(false);

  const deleteWithRetry = useCallback(async (doc: Document, retries = 0): Promise<DeleteResult> => {
    try {
      const response = await axiosInstance.delete(`/file/${doc.id}`, {
        params: {
          index_names: [doc.index_name],
        }
      });

      console.log('Delete response:', response);

      if (response.status === 200) {
        await fetchDocuments();
        return { success: true };
      } else if (response.status === 207) {
        console.warn('Partial success in document deletion:', response.data);
        await fetchDocuments();
        return { success: true, partialSuccess: true };
      } else {
        console.error('Unexpected response status:', response.status);
        return { success: false, error: 'Unexpected response from server' };
      }
    } catch (error: unknown) {
      console.error('Error deleting document:', error);
      let errorMessage = 'Failed to delete document. Please try again.';

      if (error instanceof AxiosError && error.response) {
        const status = error.response.status;
        if (status === 403) {
          return { success: false, error: 'You do not have permission to delete this document.' };
        } else if (status === 404) {
          return { success: false, error: 'Document not found. It may have been already deleted.' };
        } else if (status === 429) {
          return { success: false, error: 'Too many delete requests. Please try again later.' };
        } else if (status >= 500 && retries < MAX_RETRIES) {
          console.log(`Retrying delete operation (${retries + 1}/${MAX_RETRIES})...`);
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
          return deleteWithRetry(doc, retries + 1);
        } else {
          errorMessage = error.response.data?.error || error.message || errorMessage;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }

      return { success: false, error: errorMessage };
    }
  }, [fetchDocuments]);

  const handleDeleteDocument = useCallback(async (doc: Document): Promise<DeleteResult> => {
    console.log('Attempting to delete document:', doc);
    if (window.confirm(`Are you sure you want to delete "${doc.title}"?`)) {
      setIsDeleting(true);
      try {
        const result = await deleteWithRetry(doc);
        return result;
      } finally {
        setIsDeleting(false);
      }
    }
    return { success: false, cancelled: true };
  }, [deleteWithRetry]);

  return { handleDeleteDocument, isDeleting };
};

export default useDocumentDeletion;
