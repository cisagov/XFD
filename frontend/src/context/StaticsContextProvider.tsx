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

  const { apiGet } = useAuthContext();
  const fetchRegions = useCallback(async () => {
    try {
      const results = await apiGet('/regions');
      setRegions(
        results
          .sort((a: string, b: string) => parseInt(a) - parseInt(b))
          .map((region: { regionId: string }) => region.regionId)
      );
    } catch (e) {
      console.log(e);
    }
  }, []);

  useEffect(() => {
    fetchRegions();
  }, []);

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
