import React, { useContext } from 'react';
import { SavedSearch } from '../types/saved-search';

export interface SavedSearchContextType {
  savedSearches: SavedSearch[];
  setSavedSearches: (savedSearches: SavedSearch[]) => void;
  savedSearchCount: number;
  setSavedSearchCount: (savedSearchCount: number) => void;
}

export const SavedSearchContext = React.createContext<SavedSearchContextType>(
  undefined!
);

export const useSavedSearchContext = (): SavedSearchContextType => {
  return useContext(SavedSearchContext);
};
