/**
 * Custom hook for keyboard navigation in table components
 *
 * Provides comprehensive keyboard accessibility features including:
 * - Arrow key navigation (Up/Down)
 * - Home/End key support for jumping to first/last items
 * - Proper Tab/Shift+Tab behavior
 * - Focus management and visual indicators
 * - ARIA attributes for screen readers
 *
 */

// React Hooks
import { useCallback, useEffect, useState } from 'react';

// Configuration options for keyboard navigation behavior
interface KeyboardNavigationOptions {
  itemCount: number;
  initialFocusIndex?: number;
  onFocusChange?: (index: number) => void;
  disabled?: boolean;
}

// Return value from useKeyboardNavigation hook
interface KeyboardNavigationResult {
  focusedIndex: number;
  setFocusedIndex: (index: number) => void;
  handleKeyDown: (event: React.KeyboardEvent) => void;
  getTabIndex: (index: number) => number;
  getFocusProps: (index: number) => {
    tabIndex: number;
    'data-focused': boolean;
    'aria-current': boolean;
    onFocus: () => void;
  };
}

export function useKeyboardNavigation({
  itemCount,
  initialFocusIndex = -1,
  onFocusChange,
  disabled = false
}: KeyboardNavigationOptions): KeyboardNavigationResult {
  const [focusedIndex, setFocusedIndex] = useState(initialFocusIndex);

  // Update focus when index changes
  useEffect(() => {
    // Prevent the callback from firing when no item is focused
    if (onFocusChange && focusedIndex !== -1) {
      onFocusChange(focusedIndex);
    }
  }, [focusedIndex, onFocusChange]);

  // Memoized keyboard event handler for turning keyboard input into focus
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (disabled || itemCount === 0) return;

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setFocusedIndex((prevIndex) => {
            if (prevIndex === -1) return 0;
            return prevIndex < itemCount - 1 ? prevIndex + 1 : prevIndex;
          });
          break;

        case 'ArrowUp':
          event.preventDefault();
          setFocusedIndex((prevIndex) => {
            if (prevIndex === -1) return itemCount - 1;
            return prevIndex > 0 ? prevIndex - 1 : prevIndex;
          });
          break;

        case 'Home':
          event.preventDefault();
          setFocusedIndex(0);
          break;

        case 'End':
          event.preventDefault();
          setFocusedIndex(itemCount - 1);
          break;

        case 'Tab':
          // Allow natural tab behavior and reset focus when tabbing away
          setFocusedIndex(-1);
          break;

        case 'Enter':
        case ' ':
          // Space and Enter can be handled by parent component
          // Don't prevent default to allow natural behavior
          break;

        default:
          break;
      }
    },
    [disabled, itemCount]
  );

  // Memoized utility that determines the appropriate tabIndex value for navigable items in the collection
  const getTabIndex = useCallback(
    (_index: number) => {
      if (disabled) return -1;

      // Make all items tabbable so users can Tab through each row
      return 0;
    },
    [disabled]
  );

  // Memoized utility that creates a standardized set of props for making list items properly focusable and accessible
  const getFocusProps = useCallback(
    (index: number) => ({
      tabIndex: getTabIndex(index),
      'data-focused': focusedIndex === index,
      'aria-current': focusedIndex === index,
      onFocus: () => setFocusedIndex(index)
    }),
    [focusedIndex, getTabIndex, setFocusedIndex]
  );

  return {
    focusedIndex,
    setFocusedIndex,
    handleKeyDown,
    getTabIndex,
    getFocusProps
  };
}
