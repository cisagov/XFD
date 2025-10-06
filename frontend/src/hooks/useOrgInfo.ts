import { useMemo } from 'react';
import { ORGANIZATION_FILTER_KEY } from 'components/FilterDrawer/VSDashRegionAndOrgFilters';
import { OrganizationShallow } from 'components/FilterDrawer/RegionAndOrganizationFilters';

export function useOrgInfo(filters: any[], currentOrganization: any) {
  const orgId = useMemo(() => {
    const organizationFilter = filters.find(
      (filter) => filter.field === ORGANIZATION_FILTER_KEY
    );
    return (
      organizationFilter?.values[0]?.id ||
      organizationFilter?.values[0] ||
      currentOrganization?.id ||
      (currentOrganization as OrganizationShallow)?.id
    );
  }, [filters, currentOrganization]);

  const organizationFilter = filters.find(
    (filter) => filter.field === ORGANIZATION_FILTER_KEY
  );

  const orgName = organizationFilter?.values[0]?.name
    ? organizationFilter?.values[0]?.name
    : currentOrganization?.name;

  return { orgId, orgName };
}
