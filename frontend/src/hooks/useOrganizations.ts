// hooks/useOrganizations.ts
import { useApiGet } from './useApiGet';
import { ENDPOINTS } from '@/constants/endpoints';
import { Organization } from 'types';

export function useOrganizations(regionId?: string | null) {
  const endpoint = regionId
    ? ENDPOINTS.ORGANIZATIONS_REGION.replace('{region_id}', regionId)
    : null;

  const result = useApiGet<Organization[]>(
    endpoint,
    [regionId],
    'Failed to fetch organizations.'
  );

  return {
    ...result,
    organizations: result.data
  };
}
