import { useEffect, useState } from 'react';
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

  useEffect(() => {
    let cancelled = false;

    const fetchOrganizations = async () => {
      const stateAbbreviation = getStateAbbreviation(state);
      if (!stateAbbreviation) {
        if (!cancelled) {
          setOrganizations([]);
          setErrorMessage('');
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      try {
        const rows = await apiGet<Organization[]>(
          ENDPOINTS.ORGANIZATIONS_STATE.replace('{state}', stateAbbreviation)
        );

        if (!cancelled) {
          setOrganizations(rows);
          setErrorMessage('');
        }
      } catch (error: unknown) {
        if (!cancelled) {
          setOrganizations([]);
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Unable to fetch organizations.'
          );
          logger.error('UseOrganizationsByState failed', { error, state });
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void fetchOrganizations();

    return () => {
      cancelled = true;
    };
  }, [apiGet, state]);

  return { organizations, isLoading, errorMessage };
};
