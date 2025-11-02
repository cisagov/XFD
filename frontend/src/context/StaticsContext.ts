import React, { useContext } from 'react';

export type Region = string;

export interface StaticsContextType {
  regions: string[];
  setRegions: (regions: StaticsContextType['regions']) => void;
}

export const StaticsContext = React.createContext<StaticsContextType>(
  undefined!
);

export const useStaticsContext = (): StaticsContextType => {
  return useContext(StaticsContext);
};
