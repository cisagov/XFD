import React, { useContext } from 'react';

export interface OrganizationShallow {
  regionId: string;
  name: string;
  id: string;
  rootDomains: string[];
}

export type Region = string;

export interface FilterContextType {
  regions: Array<Region>;
  organizations: OrganizationShallow[];
  setRegions: (regions: FilterContextType['regions']) => void;
  setOrganizations: (organizations: FilterContextType['organizations']) => void;
  addOrganization: (organization: OrganizationShallow) => void;
  removeOrganization: (organization: OrganizationShallow) => void;
}

export const FilterContext = React.createContext<FilterContextType>(undefined!);

export const useFilterContext = (): FilterContextType => {
  return useContext(FilterContext);
};
