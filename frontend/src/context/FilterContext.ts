import React, { useContext, createContext } from 'react';

export interface OrganizationShallow {
  regionId: string;
  name: string;
  id: string;
  rootDomains: string[];
}

export type Region = string;

export interface FilterContext {
  regions: Array<Region>;
  organizations: OrganizationShallow[];
  setRegions: (regions: FilterContext['regions']) => void;
  setOrganizations: (organizations: FilterContext['organizations']) => void;
  addOrganization: (organization: OrganizationShallow) => void;
  removeOrganization: (organization: OrganizationShallow) => void;
}

export const FilterContext = React.createContext<FilterContext>(undefined!);

export const useFilterContext = (): FilterContext => {
  return useContext(FilterContext);
};
