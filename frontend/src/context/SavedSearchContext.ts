import React, { useContext } from 'react';
import { SavedSearch } from '../types/saved-search';

export interface SavedSearchContextType {
  savedSearches: SavedSearch[];
  setSavedSearches: (savedSearches: SavedSearch[]) => void;
  savedSearchCount: number;
  setSavedSearchCount: (savedSearchCount: number) => void;
  activeSearchId: string;
  setActiveSearchId: (activeSearchId: string) => void;
  selectedSearch: SavedSearch | null;
  setSelectedSearch: (selectedSearch: SavedSearch | null) => void;
  activeSearch: SavedSearch | undefined;
}

export const SavedSearchContext = React.createContext<SavedSearchContextType>(
  undefined!
);

export const useSavedSearchContext = (): SavedSearchContextType => {
  return useContext(SavedSearchContext);
};
