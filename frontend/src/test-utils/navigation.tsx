/**
 * Navigation testing utilities for NavigationContextProvider tests
 * Provides reusable test components, mock data, and utilities for testing navigation context functionality
 */

import React from 'react';
import { vi } from 'vitest';
import { useNavigationContext } from '../context/NavigationContext';
import { ROUTES } from '../constants/routes';

/**
 * Props for the test component that consumes NavigationContext
 */
export interface NavigationTestComponentProps {
  testId?: string;
  onMarkDrillDown?: (source: string, target: string) => void;
  onClearDrillDown?: () => void;
  onSetAllRegionsSelected?: (selected: boolean) => void;
  onIsReturningFromDrillDown?: (currentRoute: string) => void;
}

/**
 * Reusable test component that consumes NavigationContext and exposes all context values
 * through data-testid attributes for easy testing
 */
export const NavigationTestComponent: React.FC<
  NavigationTestComponentProps
> = ({
  testId = 'navigation-test-component',
  onMarkDrillDown,
  onClearDrillDown,
  onSetAllRegionsSelected,
  onIsReturningFromDrillDown
}) => {
  const {
    isDrillDown,
    sourceRoute,
    targetRoute,
    wasAllRegionsSelected,
    markDrillDown,
    clearDrillDown,
    setAllRegionsSelected,
    isReturningFromDrillDown
  } = useNavigationContext();

  return (
    <div data-testid={testId}>
      <div data-testid="isDrillDown">{isDrillDown.toString()}</div>
      <div data-testid="sourceRoute">{sourceRoute || 'null'}</div>
      <div data-testid="targetRoute">{targetRoute || 'null'}</div>
      <div data-testid="wasAllRegionsSelected">
        {wasAllRegionsSelected.toString()}
      </div>
      <button
        data-testid="markDrillDown"
        onClick={() => {
          const source = ROUTES.VSDASHBOARD;
          const target = ROUTES.VULNERABILITIES;
          markDrillDown(source, target);
          onMarkDrillDown?.(source, target);
        }}
      >
        Mark Drill Down
      </button>
      <button
        data-testid="clearDrillDown"
        onClick={() => {
          clearDrillDown();
          onClearDrillDown?.();
        }}
      >
        Clear Drill Down
      </button>
      <button
        data-testid="setAllRegionsSelected"
        onClick={() => {
          setAllRegionsSelected(true);
          onSetAllRegionsSelected?.(true);
        }}
      >
        Set All Regions Selected
      </button>
      <button
        data-testid="isReturningFromDrillDown"
        onClick={() => {
          const _result = isReturningFromDrillDown(ROUTES.VSDASHBOARD);
          onIsReturningFromDrillDown?.(ROUTES.VSDASHBOARD);
        }}
      >
        Check Is Returning
      </button>
    </div>
  );
};

/**
 * Test component that tries to use NavigationContext without provider (for error testing)
 */
export const ComponentWithoutProvider: React.FC = () => {
  const _context = useNavigationContext();
  return <div>Should not render</div>;
};

/**
 * Test component for testing different drill down routes
 */
export const TestComponentWithDifferentRoutes: React.FC<{
  onMarkDrillDown: (source: string, target: string) => void;
}> = ({ onMarkDrillDown }) => {
  const { markDrillDown } = useNavigationContext();
  return (
    <button
      data-testid="markDrillDownDifferent"
      onClick={() => {
        const newSource = ROUTES.DOMAINS;
        const newTarget = ROUTES.DOMAIN;
        markDrillDown(newSource, newTarget);
        onMarkDrillDown(newSource, newTarget);
      }}
    >
      Mark Different Drill Down
    </button>
  );
};

/**
 * Test component for testing empty routes
 */
export const TestComponentWithEmptyRoutes: React.FC = () => {
  const { markDrillDown, sourceRoute, targetRoute, isDrillDown } =
    useNavigationContext();
  return (
    <div>
      <div data-testid="isDrillDown">{isDrillDown.toString()}</div>
      <div data-testid="sourceRoute">{sourceRoute || 'null'}</div>
      <div data-testid="targetRoute">{targetRoute || 'null'}</div>
      <button
        data-testid="markDrillDownEmpty"
        onClick={() => markDrillDown('', '')}
      >
        Mark Empty Drill Down
      </button>
    </div>
  );
};

/**
 * Test component for testing toggle functionality
 */
export const TestComponentWithToggle: React.FC = () => {
  const { setAllRegionsSelected, wasAllRegionsSelected } =
    useNavigationContext();
  return (
    <div>
      <div data-testid="wasAllRegionsSelected">
        {wasAllRegionsSelected.toString()}
      </div>
      <button data-testid="setTrue" onClick={() => setAllRegionsSelected(true)}>
        Set True
      </button>
      <button
        data-testid="setFalse"
        onClick={() => setAllRegionsSelected(false)}
      >
        Set False
      </button>
    </div>
  );
};

/**
 * Test component for testing return from drill down functionality
 */
export const TestComponentForReturning: React.FC<{
  onCheckReturning?: (isReturning: boolean) => void;
  routeToCheck?: string;
}> = ({ onCheckReturning, routeToCheck = ROUTES.VSDASHBOARD }) => {
  const { markDrillDown, isReturningFromDrillDown } = useNavigationContext();

  const handleCheckReturning = () => {
    const result = isReturningFromDrillDown(routeToCheck);
    onCheckReturning?.(result);
  };

  return (
    <div>
      <button
        data-testid="markDrillDown"
        onClick={() =>
          markDrillDown(ROUTES.VSDASHBOARD, ROUTES.VULNERABILITIES)
        }
      >
        Mark Drill Down
      </button>
      <button data-testid="checkReturning" onClick={handleCheckReturning}>
        Check Returning
      </button>
    </div>
  );
};

/**
 * Test component for testing edge cases with empty/null routes
 */
export const TestComponentForEdgeCases: React.FC<{
  onCheckReturningEmpty?: (isReturning: boolean) => void;
  onCheckReturningNull?: (isReturning: boolean) => void;
}> = ({ onCheckReturningEmpty, onCheckReturningNull }) => {
  const { markDrillDown, isReturningFromDrillDown } = useNavigationContext();

  const handleCheckReturningEmpty = () => {
    const result = isReturningFromDrillDown('');
    onCheckReturningEmpty?.(result);
  };

  const handleCheckReturningNull = () => {
    const result = isReturningFromDrillDown(null as any);
    onCheckReturningNull?.(result);
  };

  return (
    <div>
      <button
        data-testid="markDrillDownEmpty"
        onClick={() => markDrillDown('', ROUTES.VULNERABILITIES)}
      >
        Mark Drill Down Empty
      </button>
      <button
        data-testid="checkReturningEmpty"
        onClick={handleCheckReturningEmpty}
      >
        Check Returning Empty
      </button>
      <button
        data-testid="checkReturningNull"
        onClick={handleCheckReturningNull}
      >
        Check Returning Null
      </button>
    </div>
  );
};

/**
 * Test component for capturing context values
 */
export const TestComponentToCapture: React.FC<{
  onContextCapture: (context: any) => void;
}> = ({ onContextCapture }) => {
  const context = useNavigationContext();

  React.useEffect(() => {
    onContextCapture(context);
  }, [context, onContextCapture]);

  return <div data-testid="context-capture">Context captured</div>;
};

/**
 * Test component for testing complete state reset functionality
 */
export const TestComponentWithReset: React.FC = () => {
  const {
    isDrillDown,
    sourceRoute,
    targetRoute,
    wasAllRegionsSelected,
    markDrillDown,
    clearDrillDown,
    setAllRegionsSelected
  } = useNavigationContext();

  const handleCompleteReset = () => {
    clearDrillDown();
    setAllRegionsSelected(false);
  };

  return (
    <div>
      <div data-testid="isDrillDown">{isDrillDown.toString()}</div>
      <div data-testid="sourceRoute">{sourceRoute || 'null'}</div>
      <div data-testid="targetRoute">{targetRoute || 'null'}</div>
      <div data-testid="wasAllRegionsSelected">
        {wasAllRegionsSelected.toString()}
      </div>
      <button
        data-testid="markDrillDown"
        onClick={() => markDrillDown(ROUTES.DOMAINS, ROUTES.DOMAIN)}
      >
        Mark Drill Down
      </button>
      <button
        data-testid="setAllRegionsSelected"
        onClick={() => setAllRegionsSelected(true)}
      >
        Set All Regions Selected
      </button>
      <button data-testid="completeReset" onClick={handleCompleteReset}>
        Complete Reset
      </button>
    </div>
  );
};

/**
 * Mock functions factory for navigation tests
 */
export const createNavigationMocks = () => ({
  onMarkDrillDown: vi.fn(),
  onClearDrillDown: vi.fn(),
  onSetAllRegionsSelected: vi.fn(),
  onIsReturningFromDrillDown: vi.fn(),
  onCheckReturning: vi.fn(),
  onCheckReturningEmpty: vi.fn(),
  onCheckReturningNull: vi.fn(),
  onContextCapture: vi.fn()
});

/**
 * Common test routes for navigation testing
 */
export const testRoutes = {
  VS_DASHBOARD: ROUTES.VSDASHBOARD,
  VULNERABILITIES: ROUTES.VULNERABILITIES,
  DOMAINS: ROUTES.DOMAINS,
  DOMAIN: ROUTES.DOMAIN,
  INVENTORY: ROUTES.INVENTORY
} as const;

/**
 * Navigation state presets for testing different scenarios
 */
export const navigationStates = {
  initial: {
    isDrillDown: false,
    sourceRoute: null,
    targetRoute: null,
    wasAllRegionsSelected: false
  },
  drillDownActive: {
    isDrillDown: true,
    sourceRoute: ROUTES.VSDASHBOARD,
    targetRoute: ROUTES.VULNERABILITIES,
    wasAllRegionsSelected: false
  },
  allRegionsSelected: {
    isDrillDown: false,
    sourceRoute: null,
    targetRoute: null,
    wasAllRegionsSelected: true
  },
  complexState: {
    isDrillDown: true,
    sourceRoute: ROUTES.VSDASHBOARD,
    targetRoute: ROUTES.VULNERABILITIES,
    wasAllRegionsSelected: true
  }
} as const;
