/**
 *
 * This test suite validates the keyboard navigation functionality including:
 * - Basic initialization and state management
 * - Arrow key navigation (up/down)
 * - Home/End key navigation
 * - Tab key handling and focus reset
 * - Disabled state behavior
 * - Tab index management
 * - Focus props generation
 *
 */

// Testing framework imports
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// React imports
import { act } from 'react';

// Test utilities
import {
  keyboardEvents,
  defaultKeyboardNavOptions
} from '../../test-utils/keyboard';

// Hook under test
import { useKeyboardNavigableWidget } from '../../hooks/useKeyboardNavigableWidget';

// -------------------- Test Suite --------------------
describe('useKeyboardNavigableWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // -------------------- Basic Functionality --------------------
  describe('Basic functionality', () => {
    it('should initialize with correct default values', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      expect(result.current.focusedIndex).toBe(-1);
      expect(typeof result.current.setFocusedIndex).toBe('function');
      expect(typeof result.current.handleKeyDown).toBe('function');
      expect(typeof result.current.getTabIndex).toBe('function');
      expect(typeof result.current.getCellFocusProps).toBe('function');
    });

    it('should initialize with custom initialFocusIndex', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget({
          ...defaultKeyboardNavOptions,
          initialFocusIndex: 2
        })
      );

      expect(result.current.focusedIndex).toBe(2);
    });

    it('should update focusedIndex when setFocusedIndex is called', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      act(() => {
        result.current.setFocusedIndex(3);
      });

      expect(result.current.focusedIndex).toBe(3);
    });
  });

  // -------------------- Keyboard Navigation --------------------
  describe('Keyboard navigation', () => {
    it('should handle ArrowDown key correctly', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      const keyDownEvent = keyboardEvents.arrowDown();

      // Starting from -1, should go to 0
      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(keyDownEvent.preventDefault).toHaveBeenCalled();
      expect(result.current.focusedIndex).toBe(0);

      // From 0, should go to 1
      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(result.current.focusedIndex).toBe(1);
    });

    it('should not go beyond last item with ArrowDown', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      act(() => {
        result.current.setFocusedIndex(4); // Last item (itemCount - 1)
      });

      const keyDownEvent = keyboardEvents.arrowDown();

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(result.current.focusedIndex).toBe(4); // Should stay at last item
    });

    it('should handle ArrowUp key correctly', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      act(() => {
        result.current.setFocusedIndex(2);
      });

      const keyDownEvent = keyboardEvents.arrowUp();

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(keyDownEvent.preventDefault).toHaveBeenCalled();
      expect(result.current.focusedIndex).toBe(1);
    });

    it('should go to last item when ArrowUp from -1', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      const keyDownEvent = keyboardEvents.arrowUp();

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(result.current.focusedIndex).toBe(4); // Last item
    });

    it('should not go below first item with ArrowUp', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      act(() => {
        result.current.setFocusedIndex(0);
      });

      const keyDownEvent = keyboardEvents.arrowUp();

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(result.current.focusedIndex).toBe(0); // Should stay at first item
    });

    it('should handle Home key correctly', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      act(() => {
        result.current.setFocusedIndex(3);
      });

      const keyDownEvent = keyboardEvents.home();

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(keyDownEvent.preventDefault).toHaveBeenCalled();
      expect(result.current.focusedIndex).toBe(0);
    });

    it('should handle End key correctly', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      const keyDownEvent = keyboardEvents.end();

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(keyDownEvent.preventDefault).toHaveBeenCalled();
      expect(result.current.focusedIndex).toBe(4); // Last item
    });

    it('should reset focus index on Tab', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      act(() => {
        result.current.setFocusedIndex(2);
      });

      const keyDownEvent = keyboardEvents.tab();

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(keyDownEvent.preventDefault).not.toHaveBeenCalled(); // Should allow natural tab behavior
      expect(result.current.focusedIndex).toBe(-1);
    });

    it('should reset focus index on Shift+Tab', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      act(() => {
        result.current.setFocusedIndex(2);
      });

      const keyDownEvent = keyboardEvents.shiftTab();

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(result.current.focusedIndex).toBe(-1);
    });

    it('should ignore other keys', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      const keyDownEvent = keyboardEvents.escape();

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(keyDownEvent.preventDefault).not.toHaveBeenCalled();
      expect(result.current.focusedIndex).toBe(-1); // Should remain unchanged
    });
  });

  // -------------------- Disabled State --------------------
  describe('Disabled state', () => {
    it('should not handle keyboard events when disabled', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget({
          ...defaultKeyboardNavOptions,
          disabled: true
        })
      );

      const keyDownEvent = {
        key: 'ArrowDown',
        preventDefault: vi.fn()
      } as any;

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(result.current.focusedIndex).toBe(-1); // Should remain unchanged
    });

    it('should return -1 for tabIndex when disabled', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget({
          ...defaultKeyboardNavOptions,
          disabled: true
        })
      );

      expect(result.current.getTabIndex(0)).toBe(-1);
      expect(result.current.getTabIndex(1)).toBe(-1);
    });
  });

  // -------------------- Tab Index Management --------------------
  describe('Tab index management', () => {
    it('should implement roving tabindex pattern', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      // Initially, first item should be tabbable (focusedIndex = -1)
      expect(result.current.getTabIndex(0)).toBe(0);
      expect(result.current.getTabIndex(1)).toBe(-1);
      expect(result.current.getTabIndex(4)).toBe(-1);

      // After focusing item 2, only item 2 should be tabbable
      act(() => {
        result.current.setFocusedIndex(2);
      });

      expect(result.current.getTabIndex(0)).toBe(-1);
      expect(result.current.getTabIndex(1)).toBe(-1);
      expect(result.current.getTabIndex(2)).toBe(0);
      expect(result.current.getTabIndex(4)).toBe(-1);
    });
  });

  // -------------------- Focus Props Generation --------------------
  describe('Focus props generation', () => {
    it('should generate correct focus props for unfocused item', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      const focusProps = result.current.getCellFocusProps(0, 0);

      expect(focusProps.tabIndex).toBe(0);
      expect(focusProps['data-focused']).toBe(false);
      expect(focusProps['aria-current']).toBe(false);
      expect(typeof focusProps.onFocus).toBe('function');
    });

    it('should generate correct focus props for focused item', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      act(() => {
        result.current.setFocusedIndex(2);
      });

      const focusProps = result.current.getCellFocusProps(2, 0);

      expect(focusProps.tabIndex).toBe(0);
      expect(focusProps['data-focused']).toBe(true);
      expect(focusProps['aria-current']).toBe(true);
      expect(typeof focusProps.onFocus).toBe('function');
    });

    it('should update focus index when onFocus is called', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget(defaultKeyboardNavOptions)
      );

      const focusProps = result.current.getCellFocusProps(3, 0);

      act(() => {
        focusProps.onFocus();
      });

      expect(result.current.focusedIndex).toBe(3);
    });
  });

  // -------------------- Callback Invocation --------------------
  describe('Callback invocation', () => {
    it('should call onFocusChange when focus changes', () => {
      const onFocusChange = vi.fn();
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget({
          ...defaultKeyboardNavOptions,
          onFocusChange
        })
      );

      act(() => {
        result.current.setFocusedIndex(2);
      });

      expect(onFocusChange).toHaveBeenCalledWith(2);
    });

    it('should not call onFocusChange when focus is -1', () => {
      const onFocusChange = vi.fn();
      renderHook(() =>
        useKeyboardNavigableWidget({
          ...defaultKeyboardNavOptions,
          onFocusChange
        })
      );

      expect(onFocusChange).not.toHaveBeenCalled();
    });

    it('should call onFocusChange when focus changes via keyboard', () => {
      const onFocusChange = vi.fn();
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget({
          ...defaultKeyboardNavOptions,
          onFocusChange
        })
      );

      const keyDownEvent = {
        key: 'ArrowDown',
        preventDefault: vi.fn()
      } as any;

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(onFocusChange).toHaveBeenCalledWith(0);
    });
  });

  // -------------------- Edge Cases --------------------
  describe('Edge cases', () => {
    it('should handle empty collection (itemCount = 0)', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget({
          ...defaultKeyboardNavOptions,
          itemCount: 0
        })
      );

      const keyDownEvent = {
        key: 'ArrowDown',
        preventDefault: vi.fn()
      } as any;

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(result.current.focusedIndex).toBe(-1); // Should remain unchanged
    });

    it('should handle single item collection', () => {
      const { result } = renderHook(() =>
        useKeyboardNavigableWidget({
          ...defaultKeyboardNavOptions,
          itemCount: 1
        })
      );

      // Arrow down should go to item 0
      const keyDownEvent = {
        key: 'ArrowDown',
        preventDefault: vi.fn()
      } as any;

      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(result.current.focusedIndex).toBe(0);

      // Another arrow down should stay at 0
      act(() => {
        result.current.handleKeyDown(keyDownEvent);
      });

      expect(result.current.focusedIndex).toBe(0);
    });
  });
});
