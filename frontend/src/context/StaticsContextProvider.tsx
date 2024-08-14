import React, { useCallback, useEffect, useMemo } from 'react';

import { usePersistentState } from 'hooks';
import { StaticsContext } from './StaticsContext';
import { useAuthContext } from './AuthContext';

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
      const results = await apiGet('/regions');
      setRegions(
        results
          .map((region: { regionId: string }) => region.regionId)
          .sort((a: string, b: string) => a.localeCompare(b))
      );
    } catch (e) {
      console.log(e);
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
