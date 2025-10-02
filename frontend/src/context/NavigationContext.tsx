/*
    Author: Jesse Salinas
    Date: 2025-10-02
    Description: Navigation context to track drill-down vs general navigation for filter persistence
*/

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface NavigationContextType {
  isDrillDown: boolean;
  sourceRoute: string | null;
  targetRoute: string | null;
  markDrillDown: (sourceRoute: string, targetRoute: string) => void;
  clearDrillDown: () => void;
  isReturningFromDrillDown: (currentRoute: string) => boolean;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

interface NavigationProviderProps {
  children: ReactNode;
}

export const NavigationProvider: React.FC<NavigationProviderProps> = ({ children }) => {
  const [isDrillDown, setIsDrillDown] = useState(false);
  const [sourceRoute, setSourceRoute] = useState<string | null>(null);
  const [targetRoute, setTargetRoute] = useState<string | null>(null);

  const markDrillDown = (source: string, target: string) => {
    console.log(`[NavigationContext] Marking drill-down: ${source} → ${target}`);
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

  // No need for sessionStorage - drill-down state should be ephemeral
  // React state naturally persists during navigation and resets on page reload

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

export const useNavigationContext = () => {
  const context = useContext(NavigationContext);
  if (context === undefined) {
    throw new Error('useNavigationContext must be used within a NavigationProvider');
  }
  return context;
};

// Helper function to determine if a route is VS Dashboard
export const isVSDashboard = (route: string) => {
  return route === '/VSDashboard' || route.startsWith('/VSDashboard');
};

// Helper function to determine if a route is a drill-down destination
export const isDrillDownDestination = (route: string) => {
  return (
    route.startsWith('/inventory/vulnerability/') ||
    route.startsWith('/inventory/domain/') ||
    route === '/inventory/vulnerabilities'
  );
};
