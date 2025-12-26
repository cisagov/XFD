/**
 * Path: frontend/src/tests/utils/numberUtils.test.ts
 * Author: Jesse Salinas
 * Date: 2025-12-26
 * Description: Tests for the formatCount utility function.
 *
 */
import { describe, it, expect } from 'vitest';
import { formatCount } from '../../utils/numberUtils';

describe('formatCount', () => {
  describe('numbers >= 1,000 should have comma separators', () => {
    it('formats 1,000 correctly', () => {
      expect(formatCount(1000)).toBe('1,000');
    });

    it('formats numbers in thousands range', () => {
      expect(formatCount(1500)).toBe('1,500');
      expect(formatCount(9999)).toBe('9,999');
    });

    it('formats numbers in ten-thousands range', () => {
      expect(formatCount(10000)).toBe('10,000');
      expect(formatCount(99999)).toBe('99,999');
    });

    it('formats numbers in hundreds-thousands range', () => {
      expect(formatCount(100000)).toBe('100,000');
      expect(formatCount(999999)).toBe('999,999');
    });

    it('formats numbers in millions range', () => {
      expect(formatCount(1000000)).toBe('1,000,000');
      expect(formatCount(1234567)).toBe('1,234,567');
    });

    it('formats numbers in billions range', () => {
      expect(formatCount(1000000000)).toBe('1,000,000,000');
      expect(formatCount(1234567890)).toBe('1,234,567,890');
    });

    it('formats negative numbers >= 1,000 in absolute value', () => {
      expect(formatCount(-1500)).toBe('-1,500');
      expect(formatCount(-1000000)).toBe('-1,000,000');
    });
  });

  describe('numbers < 1,000 should remain unformatted', () => {
    it('handles zero', () => {
      expect(formatCount(0)).toBe('0');
    });

    it('handles single digits', () => {
      expect(formatCount(1)).toBe('1');
      expect(formatCount(9)).toBe('9');
    });

    it('handles double digits', () => {
      expect(formatCount(10)).toBe('10');
      expect(formatCount(50)).toBe('50');
      expect(formatCount(99)).toBe('99');
    });

    it('handles triple digits', () => {
      expect(formatCount(100)).toBe('100');
      expect(formatCount(500)).toBe('500');
      expect(formatCount(999)).toBe('999');
    });

    it('handles small negative numbers', () => {
      expect(formatCount(-1)).toBe('-1');
      expect(formatCount(-50)).toBe('-50');
      expect(formatCount(-999)).toBe('-999');
    });
  });

  describe('edge cases and error handling', () => {
    it('handles null values', () => {
      expect(formatCount(null)).toBe('0');
    });

    it('handles undefined values', () => {
      expect(formatCount(undefined)).toBe('0');
    });

    it('handles NaN values', () => {
      expect(formatCount(NaN)).toBe('0');
    });

    it('handles decimal numbers correctly', () => {
      // Decimals < 1000 remain unformatted
      expect(formatCount(999.99)).toBe('999.99');
      expect(formatCount(500.5)).toBe('500.5');

      // Decimals >= 1000 get comma formatting
      expect(formatCount(1000.5)).toBe('1,000.5');
      expect(formatCount(1234.567)).toBe('1,234.567');
    });

    it('handles very large numbers', () => {
      expect(formatCount(123456789012345)).toBe('123,456,789,012,345');
    });
  });

  describe('acceptance criteria validation', () => {
    it('satisfies requirement: numbers >= 1,000 get comma separators', () => {
      const testCases = [
        { input: 1000, expected: '1,000' },
        { input: 10000, expected: '10,000' },
        { input: 1000000, expected: '1,000,000' },
        { input: 1000000000, expected: '1,000,000,000' }
      ];

      testCases.forEach(({ input, expected }) => {
        expect(formatCount(input)).toBe(expected);
      });
    });

    it('satisfies requirement: numbers < 1,000 remain unformatted', () => {
      const testCases = [0, 1, 50, 999];

      testCases.forEach((input) => {
        expect(formatCount(input)).toBe(input.toString());
      });
    });

    it('maintains original data types for calculations', () => {
      // The utility returns strings for display but doesn't modify original data
      const originalValue = 1500;
      const formatted = formatCount(originalValue);

      expect(typeof originalValue).toBe('number'); // Original remains a number
      expect(typeof formatted).toBe('string'); // Formatted is a string
      expect(originalValue).toBe(1500); // Original value unchanged
    });
  });
});
