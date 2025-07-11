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

  return (
    <FilterDrawerContext.Provider
      value={{ isFilterDrawerOpen, setIsFilterDrawerOpen }}
    >
      {children}
    </FilterDrawerContext.Provider>
  );
};
