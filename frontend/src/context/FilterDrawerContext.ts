import React, { useContext } from 'react';

export interface FilterDrawerContextType {
  isFilterDrawerOpen: boolean;
  setIsFilterDrawerOpen: (isFilterDrawerOpen: boolean) => void;
  selectedRegionId: string | null;
  setSelectedRegionId: (id: string | null) => void;
  selectedOrgName: string | null;
  setSelectedOrgName: (id: string | null) => void;
}

export const FilterDrawerContext = React.createContext<FilterDrawerContextType>(
  undefined!
);

export const useFilterDrawerContext = (): FilterDrawerContextType => {
  return useContext(FilterDrawerContext);
};
