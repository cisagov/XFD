/**
 *
 * Provides common keyboard event mocks and utilities for testing
 * keyboard navigation and accessibility features.
 */

import { vi } from 'vitest';
import type { KeyboardEvent } from 'react';

/**
 * Creates a mock keyboard event object for testing
 */
export const createMockKeyEvent = (
  key: string,
  options: Partial<KeyboardEvent> = {}
): any => ({
  key,
  preventDefault: vi.fn(),
  shiftKey: false,
  ctrlKey: false,
  altKey: false,
  metaKey: false,
  ...options
});

/**
 * Common keyboard event presets for testing
 */
export const keyboardEvents = {
  arrowDown: () => createMockKeyEvent('ArrowDown'),
  arrowUp: () => createMockKeyEvent('ArrowUp'),
  arrowLeft: () => createMockKeyEvent('ArrowLeft'),
  arrowRight: () => createMockKeyEvent('ArrowRight'),
  home: () => createMockKeyEvent('Home'),
  end: () => createMockKeyEvent('End'),
  tab: () => createMockKeyEvent('Tab'),
  shiftTab: () => createMockKeyEvent('Tab', { shiftKey: true }),
  enter: () => createMockKeyEvent('Enter'),
  space: () => createMockKeyEvent(' '),
  escape: () => createMockKeyEvent('Escape')
} as const;

/**
 * Default options for keyboard navigation hook testing
 */
export const defaultKeyboardNavOptions = {
  itemCount: 5,
  initialFocusIndex: -1,
  disabled: false
} as const;
