/*
    Author: Jesse Salinas
    Date: 2025-10-02
    Description: Navigation context provider implementation for drill-down state management
*/

import React, { useState, ReactNode } from 'react';
import { NavigationContext, NavigationContextType } from './NavigationContext';

interface NavigationProviderProps {
  children: ReactNode;
}

export const NavigationProvider: React.FC<NavigationProviderProps> = ({
  children
}) => {
  const [isDrillDown, setIsDrillDown] = useState(false);
  const [sourceRoute, setSourceRoute] = useState<string | null>(null);
  const [targetRoute, setTargetRoute] = useState<string | null>(null);
  const [wasAllRegionsSelected, setWasAllRegionsSelected] = useState(false);

  const markDrillDown = (source: string, target: string) => {
    setIsDrillDown(true);
    setSourceRoute(source);
    setTargetRoute(target);
  };

  const clearDrillDown = () => {
    setIsDrillDown(false);
    setSourceRoute(null);
    setTargetRoute(null);
    // Don't reset wasAllRegionsSelected here - let it persist for subsequent drill-downs
  };

  const setAllRegionsSelected = (selected: boolean) => {
    setWasAllRegionsSelected(selected);
  };

  const isReturningFromDrillDown = (currentRoute: string) => {
    // Check if we're returning to the source route from a drill-down
    return isDrillDown && sourceRoute === currentRoute;
  };

  const value: NavigationContextType = {
    isDrillDown,
    sourceRoute,
    targetRoute,
    wasAllRegionsSelected,
    markDrillDown,
    clearDrillDown,
    setAllRegionsSelected,
    isReturningFromDrillDown
  };

  return (
    <NavigationContext.Provider value={value}>
      {children}
    </NavigationContext.Provider>
  );
};
