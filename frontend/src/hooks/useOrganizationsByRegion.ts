import { useCallback, useEffect, useState } from 'react';
import { useAuthContext } from 'context';
import type { Organization } from 'types';
import { ENDPOINTS } from '@/constants/endpoints';
import { logger } from '@/utils/logger';

type UseOrganizationsByRegionResult = {
  organizations: Organization[];
  isLoading: boolean;
  errorMessage: string;
};

export const useOrganizationsByRegion = (
  regionId: string
): UseOrganizationsByRegionResult => {
  const { apiGet } = useAuthContext();

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const fetchOrganizations = useCallback(async (): Promise<void> => {
    if (!regionId) {
      setOrganizations([]);
      setErrorMessage('');
      return;
    }

    setIsLoading(true);
    try {
      const rows = await apiGet<Organization[]>(
        ENDPOINTS.ORGANIZATIONS_REGION.replace('{region_id}', regionId)
      );
      setOrganizations(rows);
      setErrorMessage('');
    } catch (error: any) {
      setOrganizations([]);
      setErrorMessage(error.message);
      logger.error('useOrganizationsByRegion failed', { error, regionId });
    } finally {
      setIsLoading(false);
    }
  }, [apiGet, regionId]);

  useEffect(() => {
    let isActive = true;

    const run = async () => {
      if (!isActive) return;
      await fetchOrganizations();
    };

    run();

    return () => {
      isActive = false;
    };
  }, [fetchOrganizations]);

  return { organizations, isLoading, errorMessage };
};
