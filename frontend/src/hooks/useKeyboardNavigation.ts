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

// Interface Definitions
interface KeyboardNavigationOptions {
  itemCount: number;
  initialFocusIndex?: number;
  onFocusChange?: (index: number) => void;
  disabled?: boolean;
}

interface KeyboardNavigationResult {
  focusedIndex: number;
  setFocusedIndex: (index: number) => void;
  handleKeyDown: (event: React.KeyboardEvent) => void;
  getTabIndex: (index: number) => number;
  getFocusProps: (index: number) => {
    tabIndex: number;
    'data-focused': boolean;
    'aria-current': boolean;
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
    if (onFocusChange && focusedIndex !== -1) {
      onFocusChange(focusedIndex);
    }
  }, [focusedIndex, onFocusChange]);

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
          // Allow natural tab behavior - don't prevent default
          // Reset focus index when tabbing away
          if (!event.shiftKey) {
            // Tabbing forward out of component
            setFocusedIndex(-1);
          } else {
            // Shift+Tab backward out of component
            setFocusedIndex(-1);
          }
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

  const getTabIndex = useCallback(
    (index: number) => {
      if (disabled) return -1;

      // If no item is focused, make first item tabbable
      if (focusedIndex === -1) {
        return index === 0 ? 0 : -1;
      }

      // Only the focused item should be tabbable
      return focusedIndex === index ? 0 : -1;
    },
    [focusedIndex, disabled]
  );

  const getFocusProps = useCallback(
    (index: number) => ({
      tabIndex: getTabIndex(index),
      'data-focused': focusedIndex === index,
      'aria-current': focusedIndex === index
    }),
    [focusedIndex, getTabIndex]
  );

  return {
    focusedIndex,
    setFocusedIndex,
    handleKeyDown,
    getTabIndex,
    getFocusProps
  };
}
