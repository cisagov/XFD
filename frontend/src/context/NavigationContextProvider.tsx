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

  const markDrillDown = (source: string, target: string) => {
    console.log(
      `[NavigationContext] Marking drill-down: ${source} → ${target}`
    );
    setIsDrillDown(true);
    setSourceRoute(source);
    setTargetRoute(target);
  };

  const clearDrillDown = () => {
    console.log('[NavigationContext] Clearing drill-down state');
    setIsDrillDown(false);
    setSourceRoute(null);
    setTargetRoute(null);
  };

  const isReturningFromDrillDown = (currentRoute: string) => {
    // Check if we're returning to the source route from a drill-down
    return isDrillDown && sourceRoute === currentRoute;
  };

  const value: NavigationContextType = {
    isDrillDown,
    sourceRoute,
    targetRoute,
    markDrillDown,
    clearDrillDown,
    isReturningFromDrillDown
  };

  return (
    <NavigationContext.Provider value={value}>
      {children}
    </NavigationContext.Provider>
  );
};
