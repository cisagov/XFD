import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { SavedSearchContext } from './SavedSearchContext';
import { SavedSearch } from '../types/saved-search';
import { useAuthContext } from './AuthContext';

interface SavedSearchContextProviderProps {
  children: React.ReactNode;
}

export const SavedSearchContextProvider: React.FC<
  SavedSearchContextProviderProps
> = ({ children }) => {
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [savedSearchCount, setSavedSearchCount] = useState<number>(0);
  const [activeSearchId, setActiveSearchId] = useState<string>('');
  const [selectedSearch, setSelectedSearch] = useState<SavedSearch | null>(
    null
  );
  const { apiGet, user } = useAuthContext();

  const fetchSearches = useCallback(async () => {
    try {
      const response = await apiGet('/saved-searches');
      setSavedSearches(response.result);
      setSavedSearchCount(response.result.length);
    } catch (e) {
      console.log(e);
    }
  }, [apiGet, setSavedSearches, setSavedSearchCount]);

  const activeSearch = useMemo(() => {
    return savedSearches.find((search) => search.id === activeSearchId);
  }, [activeSearchId, savedSearches]);

  useEffect(() => {
    if (user) fetchSearches();
  }, [user, fetchSearches]);

  const memoizedSavedSearches = useMemo(() => {
    return savedSearches;
  }, [savedSearches]);

  const memoizedSavedSearchCount = useMemo(() => {
    return savedSearchCount;
  }, [savedSearchCount]);
  return (
    <SavedSearchContext.Provider
      value={{
        savedSearches: memoizedSavedSearches,
        setSavedSearches,
        savedSearchCount: memoizedSavedSearchCount,
        setSavedSearchCount,
        activeSearchId,
        setActiveSearchId,
        selectedSearch,
        setSelectedSearch,
        activeSearch
      }}
    >
      {children}
    </SavedSearchContext.Provider>
  );
};
