import { useCallback, useEffect, useState } from 'react';
import { useAuthContext } from 'context';
import type { Organization } from 'types';
import { ENDPOINTS } from '@/constants/endpoints';
import { logger } from '@/utils/logger';
import { getStateAbbreviation } from '@/utils/stringUtils';

type UseOrganizationsByStateResult = {
  organizations: Organization[];
  isLoading: boolean;
  errorMessage: string;
};

export const useOrganizationsByState = (
  state: string
): UseOrganizationsByStateResult => {
  const { apiGet } = useAuthContext();

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const fetchOrganizations = useCallback(async (): Promise<void> => {
    const stateAbbreviation = getStateAbbreviation(state);
    if (!stateAbbreviation) {
      setOrganizations([]);
      setErrorMessage('');
      return;
    }

    setIsLoading(true);
    try {
      const rows = await apiGet<Organization[]>(
        ENDPOINTS.ORGANIZATIONS_STATE.replace('{state}', stateAbbreviation)
      );
      setOrganizations(rows);
      setErrorMessage('');
    } catch (error: any) {
      setOrganizations([]);
      setErrorMessage(error.message);
      logger.error('UseOrganizationsByState failed', { error, state });
    } finally {
      setIsLoading(false);
    }
  }, [apiGet, state]);

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
