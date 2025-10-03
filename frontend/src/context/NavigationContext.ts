/*
  Author: Jesse Salinas
  Date: 2025-10-02
	Description: Navigation context to track drill-down vs general navigation for filter persistence
*/

import React, { useContext } from 'react';

export interface NavigationContextType {
  isDrillDown: boolean;
  sourceRoute: string | null;
  targetRoute: string | null;
  markDrillDown: (sourceRoute: string, targetRoute: string) => void;
  clearDrillDown: () => void;
  isReturningFromDrillDown: (currentRoute: string) => boolean;
}

export const NavigationContext = React.createContext<NavigationContextType>(
  undefined!
);

export const useNavigationContext = (): NavigationContextType => {
  const context = useContext(NavigationContext);
  if (context === undefined) {
    throw new Error(
      'useNavigationContext must be used within a NavigationProvider'
    );
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
    route === '/inventory/vulnerabilities' ||
    route === '/inventory/domains'
  );
};
