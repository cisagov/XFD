/**
 * Unit tests for NavigationContextProvider component
 * 
 * Unit tests for the NavigationContextProvider to ensure proper behavior of:
 * - Initial state and provider defaults
 * - State updates triggered by navigation actions
 * - Consumer components reacting to state changes
 * - Error handling for invalid or unexpected state transitions
 * - Full test coverage for all branches and state transitions
 */

import React from 'react';
import { screen, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { render } from 'test-utils';
import {
  NavigationTestComponent,
  ComponentWithoutProvider,
  TestComponentWithDifferentRoutes,
  TestComponentWithEmptyRoutes,
  TestComponentWithToggle,
  TestComponentForReturning,
  TestComponentForEdgeCases,
  TestComponentToCapture,
  createNavigationMocks,
  testRoutes
} from 'test-utils/navigation';
import { useNavigationContext } from '../../context/NavigationContext';
import { NavigationProvider } from '../../context/NavigationContextProvider';

describe('NavigationContextProvider', () => {
  describe('Initial State', () => {
    it('should provide default initial state values', () => {
      render(<NavigationTestComponent />);

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('sourceRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('targetRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent(
        'false'
      );
    });

    it('should render children components', () => {
      render(<NavigationTestComponent testId="child-component" />);

      expect(screen.getByTestId('child-component')).toBeInTheDocument();
    });
  });

  describe('markDrillDown function', () => {
    it('should update drill down state when markDrillDown is called', () => {
      const { onMarkDrillDown } = createNavigationMocks();
      render(<NavigationTestComponent onMarkDrillDown={onMarkDrillDown} />);

      act(() => {
        screen.getByTestId('markDrillDown').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('true');
      expect(screen.getByTestId('sourceRoute')).toHaveTextContent(
        testRoutes.VS_DASHBOARD
      );
      expect(screen.getByTestId('targetRoute')).toHaveTextContent(
        testRoutes.VULNERABILITIES
      );
      expect(onMarkDrillDown).toHaveBeenCalledWith(
        testRoutes.VS_DASHBOARD,
        testRoutes.VULNERABILITIES
      );
    });

    it('should handle multiple markDrillDown calls with different routes', () => {
      let capturedSource: string | undefined;
      let capturedTarget: string | undefined;

      const onMarkDrillDown = vi.fn((source: string, target: string) => {
        capturedSource = source;
        capturedTarget = target;
      });

      render(<NavigationTestComponent onMarkDrillDown={onMarkDrillDown} />);

      // First drill down
      act(() => {
        screen.getByTestId('markDrillDown').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('true');
      expect(capturedSource).toBe(testRoutes.VS_DASHBOARD);
      expect(capturedTarget).toBe(testRoutes.VULNERABILITIES);

      // Reset the mock to test second call
      onMarkDrillDown.mockClear();

      render(<TestComponentWithDifferentRoutes onMarkDrillDown={onMarkDrillDown} />);

      act(() => {
        screen.getByTestId('markDrillDownDifferent').click();
      });

      expect(onMarkDrillDown).toHaveBeenCalledWith(testRoutes.DOMAINS, testRoutes.DOMAIN);
    });

    it('should handle empty or null route values', () => {
      render(<TestComponentWithEmptyRoutes />);

      act(() => {
        screen.getByTestId('markDrillDownEmpty').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('true');
      expect(screen.getByTestId('sourceRoute')).toHaveTextContent('null'); // Empty string should display as null in our component
      expect(screen.getByTestId('targetRoute')).toHaveTextContent('null');
    });
  });

  describe('clearDrillDown function', () => {
    it('should reset drill down state when clearDrillDown is called', () => {
      const { onClearDrillDown } = createNavigationMocks();
      render(<NavigationTestComponent onClearDrillDown={onClearDrillDown} />);

      // First, set drill down state
      act(() => {
        screen.getByTestId('markDrillDown').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('true');

      // Then clear it
      act(() => {
        screen.getByTestId('clearDrillDown').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('sourceRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('targetRoute')).toHaveTextContent('null');
      expect(onClearDrillDown).toHaveBeenCalled();
    });

    it('should not reset wasAllRegionsSelected when clearDrillDown is called', () => {
      render(<NavigationTestComponent />);

      // Set all regions selected
      act(() => {
        screen.getByTestId('setAllRegionsSelected').click();
      });

      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent(
        'true'
      );

      // Mark drill down
      act(() => {
        screen.getByTestId('markDrillDown').click();
      });

      // Clear drill down
      act(() => {
        screen.getByTestId('clearDrillDown').click();
      });

      // wasAllRegionsSelected should persist
      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent(
        'true'
      );
      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('false');
    });

    it('should work correctly when called multiple times', () => {
      render(<NavigationTestComponent />);

      // Mark drill down
      act(() => {
        screen.getByTestId('markDrillDown').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('true');

      // Clear multiple times
      act(() => {
        screen.getByTestId('clearDrillDown').click();
      });

      act(() => {
        screen.getByTestId('clearDrillDown').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('sourceRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('targetRoute')).toHaveTextContent('null');
    });
  });

  describe('setAllRegionsSelected function', () => {
    it('should update wasAllRegionsSelected state when setAllRegionsSelected is called', () => {
      const { onSetAllRegionsSelected } = createNavigationMocks();
      render(<NavigationTestComponent onSetAllRegionsSelected={onSetAllRegionsSelected} />);

      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent(
        'false'
      );

      act(() => {
        screen.getByTestId('setAllRegionsSelected').click();
      });

      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent(
        'true'
      );
      expect(onSetAllRegionsSelected).toHaveBeenCalledWith(true);
    });

    it('should handle toggling between true and false', () => {
      render(<TestComponentWithToggle />);

      // Initially false
      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent(
        'false'
      );

      // Set to true
      act(() => {
        screen.getByTestId('setTrue').click();
      });

      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent(
        'true'
      );

      // Set back to false
      act(() => {
        screen.getByTestId('setFalse').click();
      });

      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent(
        'false'
      );
    });
  });

  describe('isReturningFromDrillDown function', () => {
    it('should return true when current route matches source route during drill down', () => {
      let isReturning = false;
      const onCheckReturning = vi.fn((result: boolean) => {
        isReturning = result;
      });

      render(<TestComponentForReturning onCheckReturning={onCheckReturning} />);

      // Mark drill down
      act(() => {
        screen.getByTestId('markDrillDown').click();
      });

      // Check if returning from drill down
      act(() => {
        screen.getByTestId('checkReturning').click();
      });

      expect(isReturning).toBe(true);
    });

    it('should return false when current route does not match source route', () => {
      let isReturning = true; // Start with true to ensure it gets set to false
      const onCheckReturning = vi.fn((result: boolean) => {
        isReturning = result;
      });

      render(
        <TestComponentForReturning 
          onCheckReturning={onCheckReturning}
          routeToCheck={testRoutes.DOMAINS}
        />
      );

      // Mark drill down
      act(() => {
        screen.getByTestId('markDrillDown').click();
      });

      // Check if returning from drill down with different route
      act(() => {
        screen.getByTestId('checkReturning').click();
      });

      expect(isReturning).toBe(false);
    });

    it('should return false when not in drill down state', () => {
      let isReturning = true; // Start with true to ensure it gets set to false
      const onCheckReturning = vi.fn((result: boolean) => {
        isReturning = result;
      });

      render(<TestComponentForReturning onCheckReturning={onCheckReturning} />);

      // Check if returning from drill down without being in drill down state
      act(() => {
        screen.getByTestId('checkReturning').click();
      });

      expect(isReturning).toBe(false);
    });

    it('should handle edge cases with empty or null routes', () => {
      let isReturningEmpty = true;
      let isReturningNull = true;

      const onCheckReturningEmpty = vi.fn((result: boolean) => {
        isReturningEmpty = result;
      });

      const onCheckReturningNull = vi.fn((result: boolean) => {
        isReturningNull = result;
      });

      render(
        <TestComponentForEdgeCases 
          onCheckReturningEmpty={onCheckReturningEmpty}
          onCheckReturningNull={onCheckReturningNull}
        />
      );

      // Mark drill down with empty source
      act(() => {
        screen.getByTestId('markDrillDownEmpty').click();
      });

      // Check with empty string
      act(() => {
        screen.getByTestId('checkReturningEmpty').click();
      });

      // Check with null
      act(() => {
        screen.getByTestId('checkReturningNull').click();
      });

      expect(isReturningEmpty).toBe(true);
      expect(isReturningNull).toBe(false);
    });
  });

  describe('Provider Context Supply', () => {
    it('should supply all context values to consumers', () => {
      let contextValues: any = {};

      const onContextCapture = vi.fn((context: any) => {
        contextValues = context;
      });

      render(<TestComponentToCapture onContextCapture={onContextCapture} />);

      expect(contextValues).toHaveProperty('isDrillDown');
      expect(contextValues).toHaveProperty('sourceRoute');
      expect(contextValues).toHaveProperty('targetRoute');
      expect(contextValues).toHaveProperty('wasAllRegionsSelected');
      expect(contextValues).toHaveProperty('markDrillDown');
      expect(contextValues).toHaveProperty('clearDrillDown');
      expect(contextValues).toHaveProperty('setAllRegionsSelected');
      expect(contextValues).toHaveProperty('isReturningFromDrillDown');

      // Check that functions are actually functions
      expect(typeof contextValues.markDrillDown).toBe('function');
      expect(typeof contextValues.clearDrillDown).toBe('function');
      expect(typeof contextValues.setAllRegionsSelected).toBe('function');
      expect(typeof contextValues.isReturningFromDrillDown).toBe('function');
    });

    it('should update context values across multiple consumers', () => {
      const Consumer1: React.FC = () => {
        const { isDrillDown, markDrillDown } = useNavigationContext();
        return (
          <div>
            <div data-testid="consumer1-isDrillDown">{isDrillDown.toString()}</div>
            <button
              data-testid="consumer1-markDrillDown"
              onClick={() => markDrillDown(testRoutes.VS_DASHBOARD, testRoutes.VULNERABILITIES)}
            >
              Consumer 1 Mark
            </button>
          </div>
        );
      };

      const Consumer2: React.FC = () => {
        const { isDrillDown, sourceRoute } = useNavigationContext();
        return (
          <div>
            <div data-testid="consumer2-isDrillDown">{isDrillDown.toString()}</div>
            <div data-testid="consumer2-sourceRoute">{sourceRoute || 'null'}</div>
          </div>
        );
      };

      render(
        <div>
          <Consumer1 />
          <Consumer2 />
        </div>
      );

      // Initial state
      expect(screen.getByTestId('consumer1-isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('consumer2-isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('consumer2-sourceRoute')).toHaveTextContent('null');

      // Update state from consumer 1
      act(() => {
        screen.getByTestId('consumer1-markDrillDown').click();
      });

      // Both consumers should see the updated state
      expect(screen.getByTestId('consumer1-isDrillDown')).toHaveTextContent('true');
      expect(screen.getByTestId('consumer2-isDrillDown')).toHaveTextContent('true');
      expect(screen.getByTestId('consumer2-sourceRoute')).toHaveTextContent(testRoutes.VS_DASHBOARD);
    });
  });

  describe('Error Handling', () => {
    it('should throw error when useNavigationContext is used outside provider', () => {
      // Mock console.error to prevent the error from showing in test output
      const originalError = console.error;
      console.error = vi.fn();

      expect(() => {
        render(<ComponentWithoutProvider />, { wrapper: undefined });
      }).toThrow('useNavigationContext must be used within a NavigationProvider');

      // Restore console.error
      console.error = originalError;
    });

    it('should handle rapid state changes gracefully', () => {
      render(<NavigationTestComponent />);

      // Rapid state changes
      act(() => {
        for (let i = 0; i < 10; i++) {
          screen.getByTestId('markDrillDown').click();
          screen.getByTestId('clearDrillDown').click();
          screen.getByTestId('setAllRegionsSelected').click();
        }
      });

      // Final state should be consistent
      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('sourceRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('targetRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent('true');
    });
  });

  describe('State Transitions and Complex Scenarios', () => {
    it('should maintain state consistency during complex navigation flows', () => {
      render(<NavigationTestComponent />);

      // Step 1: Set all regions selected
      act(() => {
        screen.getByTestId('setAllRegionsSelected').click();
      });

      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent('true');

      // Step 2: Mark drill down
      act(() => {
        screen.getByTestId('markDrillDown').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('true');
      expect(screen.getByTestId('sourceRoute')).toHaveTextContent(testRoutes.VS_DASHBOARD);
      expect(screen.getByTestId('targetRoute')).toHaveTextContent(testRoutes.VULNERABILITIES);
      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent('true');

      // Step 3: Clear drill down (should preserve wasAllRegionsSelected)
      act(() => {
        screen.getByTestId('clearDrillDown').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('sourceRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('targetRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent('true');
    });

    it('should handle state resets properly', () => {
      const TestComponentWithReset: React.FC = () => {
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
            <div data-testid="wasAllRegionsSelected">{wasAllRegionsSelected.toString()}</div>
            <button
              data-testid="markDrillDown"
              onClick={() => markDrillDown(testRoutes.DOMAINS, testRoutes.DOMAIN)}
            >
              Mark Drill Down
            </button>
            <button data-testid="setAllRegionsSelected" onClick={() => setAllRegionsSelected(true)}>
              Set All Regions Selected
            </button>
            <button data-testid="completeReset" onClick={handleCompleteReset}>
              Complete Reset
            </button>
          </div>
        );
      };

      render(<TestComponentWithReset />);

      // Set up some state
      act(() => {
        screen.getByTestId('markDrillDown').click();
        screen.getByTestId('setAllRegionsSelected').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('true');
      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent('true');

      // Complete reset
      act(() => {
        screen.getByTestId('completeReset').click();
      });

      expect(screen.getByTestId('isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('sourceRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('targetRoute')).toHaveTextContent('null');
      expect(screen.getByTestId('wasAllRegionsSelected')).toHaveTextContent('false');
    });

    it('should handle nested provider scenarios gracefully', () => {
      // This tests that the provider doesn't interfere with nested providers
      const InnerComponent: React.FC = () => {
        const { isDrillDown, markDrillDown } = useNavigationContext();
        return (
          <div>
            <div data-testid="inner-isDrillDown">{isDrillDown.toString()}</div>
            <button
              data-testid="inner-markDrillDown"
              onClick={() => markDrillDown('inner-source', 'inner-target')}
            >
              Inner Mark
            </button>
          </div>
        );
      };

      const OuterComponent: React.FC = () => {
        const { isDrillDown } = useNavigationContext();
        return (
          <div>
            <div data-testid="outer-isDrillDown">{isDrillDown.toString()}</div>
            <NavigationProvider>
              <InnerComponent />
            </NavigationProvider>
          </div>
        );
      };

      render(<OuterComponent />);

      // Initially both should be false
      expect(screen.getByTestId('outer-isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('inner-isDrillDown')).toHaveTextContent('false');

      // Trigger inner drill down
      act(() => {
        screen.getByTestId('inner-markDrillDown').click();
      });

      // Inner should be true, outer should still be false (independent contexts)
      expect(screen.getByTestId('outer-isDrillDown')).toHaveTextContent('false');
      expect(screen.getByTestId('inner-isDrillDown')).toHaveTextContent('true');
    });
  });
});
