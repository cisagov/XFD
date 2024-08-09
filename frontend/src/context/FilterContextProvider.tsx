import React, { useState } from 'react';
import { FilterContext, OrganizationShallow, Region } from './FilterContext';
import { usePersistentState } from 'hooks';

interface FilterContextProviderProps {
  children: React.ReactNode;
}

export const FilterContextProvider: React.FC<FilterContextProviderProps> = ({
  children
}) => {
  const [regions, setRegions] = usePersistentState<Region[]>(
    'filter-regions',
    []
  );
  const [organizations, setOrganizations] = usePersistentState<
    OrganizationShallow[]
  >('filter-organizations', []);

  return (
    <FilterContext.Provider
      value={{
        regions,
        organizations,
        setOrganizations,
        setRegions
      }}
    >
      {children}
    </FilterContext.Provider>
  );
};
