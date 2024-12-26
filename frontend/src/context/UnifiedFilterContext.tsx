import React, { createContext, useContext, useReducer, useEffect, ReactNode, useMemo } from 'react';
import { FilterProps, Index } from '../types/FilterTypes';
import { useUserContext } from '../context/UserContext';

type UnifiedFilterState = {
  query: FilterProps;
  upload: FilterProps;
  availableIndices: Index[];
};

type UnifiedFilterAction =
  | { type: 'SET_QUERY_FILTERS'; payload: Partial<FilterProps> }
  | { type: 'SET_UPLOAD_FILTERS'; payload: Partial<FilterProps> }
  | { type: 'SET_AVAILABLE_INDICES'; payload: Index[] }
  | { type: 'RESET_QUERY_FILTERS' }
  | { type: 'RESET_UPLOAD_FILTERS' }
  | { type: 'RESET_ALL_FILTERS' };

const initialState: UnifiedFilterState = {
  query: {
    indices: [],
    filters: {},
    visibility: {},
  },
  upload: {
    indices: [],
    filters: {},
    visibility: {},
  },
  availableIndices: [],
};

const unifiedFilterReducer = (state: UnifiedFilterState, action: UnifiedFilterAction): UnifiedFilterState => {
  const newState = (() => {
    switch (action.type) {
      case 'SET_QUERY_FILTERS':
        return { ...state, query: { ...state.query, ...action.payload } };
      case 'SET_UPLOAD_FILTERS':
        return { ...state, upload: { ...state.upload, ...action.payload } };
      case 'SET_AVAILABLE_INDICES':
        return { ...state, availableIndices: action.payload };
      case 'RESET_QUERY_FILTERS':
        return { ...state, query: initialState.query };
      case 'RESET_UPLOAD_FILTERS':
        return { ...state, upload: initialState.upload };
      case 'RESET_ALL_FILTERS':
        return initialState;
      default:
        return state;
    }
  })();

  // Debug logging for state changes
  console.log('Filter State Update:', {
    action: action.type,
    payload: 'payload' in action ? action.payload : undefined,
    prevState: state,
    newState
  });

  return newState;
};

const UnifiedFilterContext = createContext<{
  state: UnifiedFilterState;
  dispatch: React.Dispatch<UnifiedFilterAction>;
} | undefined>(undefined);

export const UnifiedFilterProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user, guestToken } = useUserContext();
  const [state, dispatch] = useReducer(unifiedFilterReducer, initialState);

  // Generate session-specific storage key
  const storageKey = useMemo(() => {
    const sessionId = user?.is_guest ? `guest_${guestToken}` : `user_${user?.id}`;
    console.log('Using storage key:', `unifiedFilterState_${sessionId}`);
    return `unifiedFilterState_${sessionId}`;
  }, [user?.is_guest, user?.id, guestToken]);

  // Load initial state from storage
  useEffect(() => {
    console.log('Loading state for session:', storageKey);
    const savedState = localStorage.getItem(storageKey);

    if (savedState) {
      try {
        const parsedState = JSON.parse(savedState);
        console.log('Loaded saved state:', parsedState);

        // Reset available indices and restore saved state
        dispatch({ type: 'SET_AVAILABLE_INDICES', payload: [] });
        dispatch({ type: 'SET_QUERY_FILTERS', payload: parsedState.query });
        dispatch({ type: 'SET_UPLOAD_FILTERS', payload: parsedState.upload });
      } catch (error) {
        console.error('Error loading filter state:', error);
        dispatch({ type: 'RESET_ALL_FILTERS' });
      }
    } else {
      console.log('No saved state found, using initial state');
      dispatch({ type: 'RESET_ALL_FILTERS' });
    }
  }, [storageKey]);

  // Persist state to localStorage
  useEffect(() => {
    console.log('Saving state for session:', storageKey, state);
    localStorage.setItem(storageKey, JSON.stringify(state));
  }, [state, storageKey]);

  // Clear state on session changes
  useEffect(() => {
    if (user?.is_guest) {
      const cleanupHandler = () => {
        console.log('Cleaning up guest session state:', storageKey);
        localStorage.removeItem(storageKey);
      };

      window.addEventListener('beforeunload', cleanupHandler);

      return () => {
        window.removeEventListener('beforeunload', cleanupHandler);
        cleanupHandler();
      };
    }
  }, [user?.is_guest, storageKey]);

  return (
    <UnifiedFilterContext.Provider value={{ state, dispatch }}>
      {children}
    </UnifiedFilterContext.Provider>
  );
};

export const useUnifiedFilter = () => {
  const context = useContext(UnifiedFilterContext);
  if (context === undefined) {
    throw new Error('useUnifiedFilter must be used within a UnifiedFilterProvider');
  }
  return context;
};

// Helper functions for common filter operations
export const setQueryFilters = (dispatch: React.Dispatch<UnifiedFilterAction>, filters: Partial<FilterProps>) => {
  dispatch({ type: 'SET_QUERY_FILTERS', payload: filters });
};

export const setUploadFilters = (dispatch: React.Dispatch<UnifiedFilterAction>, filters: Partial<FilterProps>) => {
  dispatch({ type: 'SET_UPLOAD_FILTERS', payload: filters });
};

export const setAvailableIndices = (dispatch: React.Dispatch<UnifiedFilterAction>, indices: Index[]) => {
  console.log('Setting available indices:', indices);
  dispatch({ type: 'SET_AVAILABLE_INDICES', payload: indices });
};

export const resetQueryFilters = (dispatch: React.Dispatch<UnifiedFilterAction>) => {
  dispatch({ type: 'RESET_QUERY_FILTERS' });
};

export const resetUploadFilters = (dispatch: React.Dispatch<UnifiedFilterAction>) => {
  dispatch({ type: 'RESET_UPLOAD_FILTERS' });
};

export const resetAllFilters = (dispatch: React.Dispatch<UnifiedFilterAction>) => {
  dispatch({ type: 'RESET_ALL_FILTERS' });
};
