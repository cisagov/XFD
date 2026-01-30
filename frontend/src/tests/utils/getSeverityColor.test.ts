import { describe, expect, it } from 'vitest';

import {
  getSeverityColor,
  getSeverityLevelColorMap,
  severityColor
} from '@/utils/getSeverityColor';

/**
 * Severity color utilities:
 * Validates severity-to-color mappings and ensures consistent color selection behavior.
 */
describe('severity color utilities', () => {
  /**
   * getSeverityColor:
   * Maps human-readable severity labels to fixed hex colors.
   */
  describe('getSeverityColor', () => {
    /** Returns the expected hex color for supported severities (case-insensitive). */
    it('returns correct hex color for known severities (case-insensitive)', () => {
      expect(getSeverityColor({ id: 'low' })).toBe('#FFB38A');
      expect(getSeverityColor({ id: 'Medium' })).toBe('#EC7633');
      expect(getSeverityColor({ id: 'HIGH' })).toBe('#C33200');
      expect(getSeverityColor({ id: 'critical' })).toBe('#731A00');
    });

    /** Returns an empty string for N/A, empty, or unsupported severity values. */
    it('returns empty string for unknown severities and N/A', () => {
      expect(getSeverityColor({ id: 'n/a' })).toBe('');
      expect(getSeverityColor({ id: 'N/A' })).toBe('');
      expect(getSeverityColor({ id: '' })).toBe('');
      expect(getSeverityColor({ id: 'other' })).toBe('');
    });
  });

  /**
   * getSeverityLevelColorMap:
   * Produces a theme-based mapping for severity tokens (low/medium/high/critical/all).
   */
  describe('getSeverityLevelColorMap', () => {
    /** Builds a stable severity-to-theme mapping from the provided theme palette. */
    it('creates a consistent severity-to-theme mapping', () => {
      const theme = {
        palette: {
          secondary: {
            light: 'secondary.light.value',
            main: 'secondary.main.value',
            dark: 'secondary.dark.value',
            darker: 'secondary.darker.value'
          },
          primary: {
            dark: 'primary.dark.value'
          }
        }
      };

      expect(getSeverityLevelColorMap(theme)).toEqual({
        low: 'secondary.light.value',
        medium: 'secondary.main.value',
        high: 'secondary.dark.value',
        critical: 'secondary.darker.value',
        all: 'primary.dark.value'
      });
    });
  });

  /**
   * severityColor:
   * Maps severity keys to theme palette token strings (or a default fallback color).
   */
  describe('severityColor', () => {
    /** Returns the expected palette token for supported severity keys. */
    it('returns correct palette token for known severity keys', () => {
      expect(severityColor('critical')).toBe('secondary.darker');
      expect(severityColor('high')).toBe('secondary.dark');
      expect(severityColor('medium')).toBe('secondary.main');
      expect(severityColor('low')).toBe('secondary.light');
    });

    /** Returns a default color for unknown, empty, or null severity values. */
    it('returns default color for unknown/null input', () => {
      expect(severityColor(null)).toBe('#000000');
      expect(severityColor('')).toBe('#000000');
      expect(severityColor('other')).toBe('#000000');
    });
  });
});

/**
 * Consistency checks:
 * Ensures the severity utilities agree on which severities are "recognized" and avoids contradictions.
 */
describe('severity color utilities - consistency checks', () => {
  /** Recognized severities should produce a non-empty hex color and a theme palette token. */
  it('getSeverityColor and severityColor agree on which severities are recognized', () => {
    const severities = ['low', 'medium', 'high', 'critical'];

    severities.forEach((severity) => {
      expect(getSeverityColor({ id: severity })).not.toBe('');
      expect(severityColor(severity)).toMatch(/^secondary\./);
    });
  });

  /** Unrecognized severities should consistently yield the empty-string hex fallback in getSeverityColor. */
  it('getSeverityColor returns empty string for N/A and unknown values', () => {
    ['N/A', 'n/a', '', 'other', 'unknown'].forEach((severity) => {
      expect(getSeverityColor({ id: severity })).toBe('');
    });
  });
});
