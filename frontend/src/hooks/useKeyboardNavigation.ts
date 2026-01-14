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
import { useCallback, useEffect, useState, useRef } from 'react';

// Configuration options for keyboard navigation behavior
interface KeyboardNavigationOptions {
  itemCount: number;
  columnCount?: number; // Number of columns for 2D grid navigation
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
  getCellFocusProps: (
    rowIndex: number,
    columnIndex: number
  ) => {
    tabIndex: number;
    'data-focused': boolean;
    'aria-current': boolean;
    onFocus: () => void;
    ref: (element: HTMLElement | null) => void;
  };
}

export function useKeyboardNavigation({
  itemCount,
  columnCount = 1, // Default to 1 column for backward compatibility
  initialFocusIndex = -1,
  onFocusChange,
  disabled = false
}: KeyboardNavigationOptions): KeyboardNavigationResult {
  const [focusedIndex, setFocusedIndex] = useState(initialFocusIndex);
  const cellRefs = useRef<Map<number, HTMLElement>>(new Map());

  // Convert linear index to row/column coordinates
  const getCoordinates = (index: number): { row: number; col: number } => {
    if (index === -1) return { row: -1, col: -1 };
    return {
      row: Math.floor(index / columnCount),
      col: index % columnCount
    };
  };

  // Convert row/column coordinates to linear index
  const getIndex = (row: number, col: number): number => {
    const totalRows = Math.ceil(itemCount / columnCount);
    if (row < 0 || row >= totalRows || col < 0 || col >= columnCount) return -1;
    const index = row * columnCount + col;
    return index >= itemCount ? -1 : index;
  };

  // Update focus when index changes
  useEffect(() => {
    // Prevent the callback from firing when no item is focused
    if (onFocusChange && focusedIndex !== -1) {
      onFocusChange(focusedIndex);
    }
  }, [focusedIndex, onFocusChange]);

  // Focus the actual DOM element when focusedIndex changes
  useEffect(() => {
    if (focusedIndex !== -1) {
      const element = cellRefs.current.get(focusedIndex);
      if (element && document.activeElement !== element) {
        element.focus();
      }
    }
  }, [focusedIndex]);

  // Memoized keyboard event handler for turning keyboard input into focus
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (disabled || itemCount === 0) return;

      const { row, col } = getCoordinates(focusedIndex);

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          if (focusedIndex === -1) {
            setFocusedIndex(0);
          } else if (columnCount > 1) {
            // 2D navigation: move down one row
            const newIndex = getIndex(row + 1, col);
            if (newIndex !== -1) {
              setFocusedIndex(newIndex);
            }
          } else {
            // 1D navigation: move to next item
            setFocusedIndex((prevIndex) => {
              if (prevIndex === -1) return 0;
              return prevIndex < itemCount - 1 ? prevIndex + 1 : prevIndex;
            });
          }
          break;

        case 'ArrowUp':
          event.preventDefault();
          if (focusedIndex === -1) {
            setFocusedIndex(itemCount - 1);
          } else if (columnCount > 1) {
            // 2D navigation: move up one row
            const newIndex = getIndex(row - 1, col);
            if (newIndex !== -1) {
              setFocusedIndex(newIndex);
            }
          } else {
            // 1D navigation: move to previous item
            setFocusedIndex((prevIndex) => {
              if (prevIndex === -1) return itemCount - 1;
              return prevIndex > 0 ? prevIndex - 1 : prevIndex;
            });
          }
          break;

        case 'ArrowRight':
          if (columnCount > 1) {
            event.preventDefault();
            if (focusedIndex === -1) {
              setFocusedIndex(0);
            } else {
              // 2D navigation: move right one column
              const newIndex = getIndex(row, col + 1);
              if (newIndex !== -1) {
                setFocusedIndex(newIndex);
              }
            }
          }
          break;

        case 'ArrowLeft':
          if (columnCount > 1) {
            event.preventDefault();
            if (focusedIndex === -1) {
              setFocusedIndex(0);
            } else {
              // 2D navigation: move left one column
              const newIndex = getIndex(row, col - 1);
              if (newIndex !== -1) {
                setFocusedIndex(newIndex);
              }
            }
          }
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
    [disabled, itemCount, focusedIndex, columnCount, getCoordinates, getIndex]
  );

  // Memoized utility that determines the appropriate tabIndex value for child items
  // First cell gets tabIndex 0, all others get -1
  const getTabIndex = useCallback(
    (index: number) => {
      if (disabled) return -1;

      // First cell is the tab stop, all others are -1
      return index === 0 ? 0 : -1;
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

  // Memoized utility that creates focus props for individual cells in a 2D grid
  const getCellFocusProps = useCallback(
    (rowIndex: number, columnIndex: number) => {
      const cellIndex = getIndex(rowIndex, columnIndex);
      return {
        tabIndex: getTabIndex(cellIndex),
        'data-focused': focusedIndex === cellIndex,
        'aria-current': focusedIndex === cellIndex,
        onFocus: () => setFocusedIndex(cellIndex),
        ref: (element: HTMLElement | null) => {
          if (element) {
            cellRefs.current.set(cellIndex, element);
          } else {
            cellRefs.current.delete(cellIndex);
          }
        }
      };
    },
    [focusedIndex, getTabIndex, setFocusedIndex, getIndex]
  );

  return {
    focusedIndex,
    setFocusedIndex,
    handleKeyDown,
    getTabIndex,
    getFocusProps,
    getCellFocusProps
  };
}
