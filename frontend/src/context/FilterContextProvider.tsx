import React, { useCallback, useState } from 'react';
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

  const addOrganization = useCallback(
    (organization: OrganizationShallow) => {
      const newOrgs = [...organizations, organization];
      setOrganizations(newOrgs);
    },
    [organizations]
  );

  const removeOrganization = useCallback(
    (organization: OrganizationShallow) => {
      setOrganizations(
        organizations.filter((org) => org.id !== organization.id)
      );
    },
    [organizations]
  );

  return (
    <FilterContext.Provider
      value={{
        regions,
        organizations,
        setOrganizations,
        setRegions,
        removeOrganization,
        addOrganization
      }}
    >
      {children}
    </FilterContext.Provider>
  );
};
