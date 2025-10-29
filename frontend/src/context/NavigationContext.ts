/*
  Author: Jesse Salinas
  Date: 2025-10-02
	Description: Navigation context to track drill-down vs general navigation for filter persistence
*/

import { ROUTES } from '@/constants/routes';
import React, { useContext } from 'react';

export interface NavigationContextType {
  isDrillDown: boolean;
  sourceRoute: string | null;
  targetRoute: string | null;
  wasAllRegionsSelected: boolean;
  markDrillDown: (sourceRoute: string, targetRoute: string) => void;
  clearDrillDown: () => void;
  setAllRegionsSelected: (selected: boolean) => void;
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
  return route === ROUTES.VSDASHBOARD || route.startsWith(ROUTES.VSDASHBOARD);
};

// Helper function to determine if a route is a drill-down destination
export const isDrillDownDestination = (route: string) => {
  const stripParams = (r: string) =>
    r
      .replace(/\/:[^/]+/g, '')
      .replace(/\/+/g, '/')
      .replace(/\/$/, '') || '/';
  const cleanedRoute = stripParams(route);
  const vulnRoute = stripParams(ROUTES.VULNERABILITY);
  const domainRoute = stripParams(ROUTES.DOMAIN);
  const inventoryVulnRoute = stripParams(ROUTES.VULNERABILITIES);
  const inventoryDomainsRoute = stripParams(ROUTES.DOMAINS);
  return (
    cleanedRoute === inventoryVulnRoute ||
    cleanedRoute === inventoryDomainsRoute ||
    cleanedRoute.startsWith(vulnRoute) ||
    cleanedRoute.startsWith(domainRoute)
  );
};
