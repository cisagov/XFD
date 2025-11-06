import { describe, it, expect } from 'vitest';
import { enrolledWithinTwoWeeks, formatRange } from '../dateUtils';

describe('enrolledWithinTwoWeeks', () => {
  it('returns true for a timestamp within 14 days', () => {
    const recent = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
    expect(enrolledWithinTwoWeeks(recent)).toBe(true);
  });

  it('returns false for a timestamp older than 14 days', () => {
    const old = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
    expect(enrolledWithinTwoWeeks(old)).toBe(false);
  });

  it('returns false for invalid or missing input', () => {
    expect(enrolledWithinTwoWeeks('invalid-date')).toBe(false);
    expect(enrolledWithinTwoWeeks(null)).toBe(false);
  });
});

describe('formatRange', () => {
  it('returns only the end date when both start and end are provided', () => {
    const start = '2024-01-01';
    const end = '2024-01-10';

    const expected = new Date(end).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    expect(formatRange(start, end)).toBe(expected);
  });

  it('returns only the start date when end is missing', () => {
    const start = '2024-01-01';
    const expected = new Date(start).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    expect(formatRange(start, null)).toBe(expected);
  });

  it('returns only the end date when start is missing', () => {
    const end = '2024-02-15';
    const expected = new Date(end).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    expect(formatRange(undefined, end)).toBe(expected);
  });

  it('returns "No Dates Available" when both are missing', () => {
    expect(formatRange(null, null)).toBe('No Dates Available');
  });
});
