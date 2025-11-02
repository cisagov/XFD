import React, { useContext } from 'react';

export interface FilterDrawerContextType {
  isFilterDrawerOpen: boolean;
  setIsFilterDrawerOpen: (isFilterDrawerOpen: boolean) => void;
}

export const FilterDrawerContext = React.createContext<FilterDrawerContextType>(
  undefined!
);

export const useFilterDrawerContext = (): FilterDrawerContextType => {
  return useContext(FilterDrawerContext);
};
