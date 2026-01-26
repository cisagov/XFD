import React from 'react';
import { FilterDrawerContext } from 'context/FilterDrawerContext';
import { usePersistentState } from 'hooks';

interface FilterDrawerContextProviderProps {
  children: React.ReactNode;
}

export const FilterDrawerContextProvider: React.FC<
  FilterDrawerContextProviderProps
> = ({ children }) => {
  const [isFilterDrawerOpen, setIsFilterDrawerOpen] = usePersistentState(
    'filterDrawerOpen',
    false
  );

  const [selectedRegionId, setSelectedRegionId] = React.useState<string | null>(
    null
  );
  const [selectedOrgName, setSelectedOrgName] = React.useState<string | null>(
    null
  );

  const value = React.useMemo(
    () => ({
      isFilterDrawerOpen,
      setIsFilterDrawerOpen,
      selectedRegionId,
      setSelectedRegionId,
      selectedOrgName,
      setSelectedOrgName
    }),
    [isFilterDrawerOpen, selectedRegionId, selectedOrgName]
  );

  return (
    <FilterDrawerContext.Provider value={value}>
      {children}
    </FilterDrawerContext.Provider>
  );
};
