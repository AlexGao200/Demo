import { useState, useEffect, useCallback, useMemo } from 'react';
import axiosInstance from '../axiosInstance';
import { Document } from '../types/DocumentTypes';
import { useUnifiedFilter } from '../context/UnifiedFilterContext';
import { AxiosRequestConfig } from 'axios';
import { FilterProps } from '../types/FilterTypes';

interface DocumentsResponse {
  documents?: Document[];
  groups?: { groupName: string; documents: Document[] }[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Helper function to group documents
const groupDocuments = (documents: Document[], sortField: string): { groupName: string; documents: Document[] }[] => {
  const grouped = documents.reduce((acc, doc) => {
    let groupKey = '';

    // Determine group key based on sort field
    if (sortField === 'organization') {
      groupKey = doc.organization || 'Unknown Organization';
    } else if (sortField === 'category') {
      groupKey = doc.filter_dimensions?.category || 'Uncategorized';
    } else if (sortField.startsWith('filter_dimensions.')) {
      const dimension = sortField.split('.')[1];
      groupKey = doc.filter_dimensions?.[dimension] || `No ${dimension}`;
    } else {
      groupKey = 'Other';
    }

    if (!acc[groupKey]) {
      acc[groupKey] = [];
    }
    acc[groupKey].push(doc);
    return acc;
  }, {} as Record<string, Document[]>);

  // Convert to array format expected by DocumentGrid
  return Object.entries(grouped)
    .map(([groupName, docs]) => ({
      groupName,
      documents: docs
    }))
    .sort((a, b) => a.groupName.localeCompare(b.groupName)); // Sort groups alphabetically
};

export const useFetchDocuments = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [groups, setGroups] = useState<{ groupName: string; documents: Document[] }[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalDocuments, setTotalDocuments] = useState<number>(0);
  const [sortField, setSortField] = useState<string>('title');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [error, setError] = useState<string | null>(null);
  const { state: filterState } = useUnifiedFilter();

  const fetchDocuments = useCallback(
    async (currentPage: number = 1, sortField: string = 'title', sortOrder: 'asc' | 'desc' = 'asc') => {
      console.log(`Fetching documents for page ${currentPage} with sortField: ${sortField}, sortOrder: ${sortOrder}`);

      if (!filterState.query || Object.keys(filterState.query).length === 0) {
        console.log('No filter query, skipping fetch');
        return;
      }

      setLoading(true);
      setError(null);

      // Adjust per_page based on sort field
      const per_page = sortField === 'title' ? 9 : 1000;

      // Prepare filter dimension names and values
      const filterDimNames = Object.keys(filterState.query.filters || {});
      const filterDimValues = filterDimNames.map(dim => filterState.query.filters[dim]);

      const formattedFilters: Partial<FilterProps> & {
        page: number;
        per_page: number;
        sortField: string;
        sortOrder: 'asc' | 'desc';
      } = {
        indices: filterState.query.indices,
        filterDimNames,
        filterDimValues,
        page: currentPage,
        per_page,
        sortField,
        sortOrder,
      };

      try {
        const config: AxiosRequestConfig = {
          params: formattedFilters,
        };

        const response = await axiosInstance.get<DocumentsResponse>('/filter/filter_documents', config);

        console.log('Backend response:', response.data);

        if (response.data.documents) {
          if (sortField !== 'title') {
            // Transform and group documents for non-title sorts
            const groupedDocs = groupDocuments(response.data.documents, sortField);
            console.log('Transformed groups:', groupedDocs);
            setGroups(groupedDocs);
            setDocuments([]);
          } else {
            // Handle title sort normally
            console.log('Setting documents:', response.data.documents);
            setDocuments(response.data.documents);
            setGroups([]);
          }
        } else if (response.data.groups) {
          // Handle if backend returns pre-grouped data
          console.log('Setting backend-grouped data:', response.data.groups);
          setGroups(response.data.groups);
          setDocuments([]);
        }

        setTotalPages(response.data.total_pages);
        setTotalDocuments(response.data.total);
        setPage(currentPage);
      } catch (error) {
        console.error('Error fetching documents:', error);
        setError('Failed to fetch documents. Please try again later.');
        setDocuments([]);
        setGroups([]);
      } finally {
        setLoading(false);
      }
    },
    [filterState.query]
  );

  useEffect(() => {
    fetchDocuments(1, sortField, sortOrder);
  }, [fetchDocuments, sortField, sortOrder]);

  const loadNextPage = useCallback(() => {
    if (page < totalPages) {
      console.log('Loading next page');
      fetchDocuments(page + 1, sortField, sortOrder);
    }
  }, [page, totalPages, fetchDocuments, sortField, sortOrder]);

  const loadPreviousPage = useCallback(() => {
    if (page > 1) {
      console.log('Loading previous page');
      fetchDocuments(page - 1, sortField, sortOrder);
    }
  }, [page, fetchDocuments, sortField, sortOrder]);

  return useMemo(
    () => ({
      documents,
      groups,
      loading,
      page,
      totalPages,
      totalDocuments,
      loadNextPage,
      loadPreviousPage,
      fetchDocuments,
      setSortField,
      setSortOrder,
      sortField,
      sortOrder,
      error,
    }),
    [
      documents,
      groups,
      loading,
      page,
      totalPages,
      totalDocuments,
      loadNextPage,
      loadPreviousPage,
      fetchDocuments,
      sortField,
      sortOrder,
      error,
    ]
  );
};
