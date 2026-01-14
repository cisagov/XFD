import React, { useCallback, useEffect, useMemo } from 'react';
import { logger } from '@/utils/logger';

import { usePersistentState } from 'hooks';
import { StaticsContext } from './StaticsContext';
import { useAuthContext } from './AuthContext';
import { ENDPOINTS } from '@/constants/endpoints';

interface StaticsContextProviderProps {
  children: React.ReactNode;
}

export const StaticsContextProvider: React.FC<StaticsContextProviderProps> = ({
  children
}) => {
  const [regions, setRegions] = usePersistentState<string[]>(
    'filter-regions',
    []
  );

  const { apiGet, user } = useAuthContext();
  const fetchRegions = useCallback(async () => {
    try {
      const results = await apiGet(ENDPOINTS.REGIONS);
      setRegions(
        results
          .map((region: { region_id: string }) => region.region_id)
          .sort((a: string, b: string) => {
            if (parseInt(a) < parseInt(b)) {
              return -1;
            }
            return 1;
          })
      );
    } catch (e) {
      logger.error('StaticsContextProvider.fetchRegions failed:', { error: e });
    }
  }, [apiGet, setRegions]);

  useEffect(() => {
    if (user) {
      fetchRegions();
    }
  }, [user, fetchRegions]);

  const memoizedRegions = useMemo(() => {
    return regions;
  }, [regions]);

  return (
    <StaticsContext.Provider
      value={{
        regions: memoizedRegions,
        setRegions
      }}
    >
      {children}
    </StaticsContext.Provider>
  );
};
