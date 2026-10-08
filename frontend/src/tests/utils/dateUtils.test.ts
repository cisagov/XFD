import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  enrolledWithinTwoWeeks,
  formatRange,
  toEST,
  toUTC,
  formatShortDate,
  formatDate,
  formReadableDate,
  humanReadableDate
} from '../../utils/dateUtils';

/**
 * enrolledWithinTwoWeeks:
 * Validates whether a timestamp falls within a 14-day window from "now".
 */
describe('enrolledWithinTwoWeeks', () => {
  /** Returns true when the timestamp is within the last 14 days. */
  it('returns true for a timestamp within 14 days', () => {
    const recentTimestamp = new Date(
      Date.now() - 7 * 24 * 60 * 60 * 1000
    ).toISOString();

    expect(enrolledWithinTwoWeeks(recentTimestamp)).toBe(true);
  });

  /** Returns false when the timestamp is older than 14 days. */
  it('returns false for a timestamp older than 14 days', () => {
    const oldTimestamp = new Date(
      Date.now() - 30 * 24 * 60 * 60 * 1000
    ).toISOString();

    expect(enrolledWithinTwoWeeks(oldTimestamp)).toBe(false);
  });

  /** Returns false for invalid or missing input. */
  it('returns false for invalid or missing input', () => {
    expect(enrolledWithinTwoWeeks('invalid-date')).toBe(false);
    expect(enrolledWithinTwoWeeks(null)).toBe(false);
  });
});

/**
 * formatRange:
 * Confirms date range display rules (end-only when both provided, fallback messaging).
 */
describe('formatRange', () => {
  /** When both start and end are provided, only the end date is shown (per requirements). */
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

  /** When only start is provided, start date is shown. */
  it('returns only the start date when end is missing', () => {
    const start = '2024-01-01';
    const expected = new Date(start).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    expect(formatRange(start, null)).toBe(expected);
  });

  /** When only end is provided, end date is shown. */
  it('returns only the end date when start is missing', () => {
    const end = '2024-02-15';
    const expected = new Date(end).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    expect(formatRange(undefined, end)).toBe(expected);
  });

  /** When both start and end are missing, the "No Dates Available" fallback is returned. */
  it('returns "No Dates Available" when both are missing', () => {
    expect(formatRange(null, null)).toBe('No Dates Available');
  });
});

const utcMidday = (dateOnly: string) => `${dateOnly}T12:00:00.000Z`;

const longUSDate = (dateInput: string | Date) =>
  new Date(dateInput).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

/**
 * enrolledWithinTwoWeeks (edge cases):
 * Adds deterministic boundary checks (14-day cutoff) and documents current behavior.
 */
describe('enrolledWithinTwoWeeks (additional edge cases)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-26T12:00:00.000Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /** Boundary: exactly 14 days old should be considered within range (inclusive). */
  it('returns true for a timestamp exactly 14 days ago (boundary inclusive)', () => {
    const exactTimestamp = new Date(
      Date.now() - 14 * 24 * 60 * 60 * 1000
    ).toISOString();

    expect(enrolledWithinTwoWeeks(exactTimestamp)).toBe(true);
  });

  /** Boundary: 15 days old should be outside the 14-day window. */
  it('returns false for a timestamp 15 days ago', () => {
    const oldTimestamp = new Date(
      Date.now() - 15 * 24 * 60 * 60 * 1000
    ).toISOString();

    expect(enrolledWithinTwoWeeks(oldTimestamp)).toBe(false);
  });

  /** Undefined input is treated as missing and returns false. */
  it('returns false for undefined input', () => {
    expect(enrolledWithinTwoWeeks(undefined)).toBe(false);
  });

  /** Documents current behavior: future timestamps are treated as within range. */
  it('returns true for a future timestamp (current behavior)', () => {
    const futureTimestamp = new Date(
      Date.now() + 2 * 24 * 60 * 60 * 1000
    ).toISOString();

    expect(enrolledWithinTwoWeeks(futureTimestamp)).toBe(true);
  });
});

/**
 * formatShortDate:
 * Ensures short date formatting returns user-friendly strings and safe fallbacks.
 */
describe('formatShortDate', () => {
  /** Null/undefined inputs produce an empty string. */
  it('returns empty string for null/undefined', () => {
    expect(formatShortDate(null)).toBe('');
    expect(formatShortDate(undefined)).toBe('');
  });

  /** Invalid date strings produce an empty string. */
  it('returns empty string for invalid input', () => {
    expect(formatShortDate('not-a-date')).toBe('');
  });

  /** Valid date strings are formatted into a long US date format. */
  it('formats a valid date string as "Month day, year"', () => {
    const input = utcMidday('2024-06-15');
    expect(formatShortDate(input)).toBe(longUSDate(input));
  });

  /** Date objects are accepted and formatted consistently. */
  it('accepts Date objects', () => {
    const dateObj = new Date(utcMidday('2024-06-15'));
    expect(formatShortDate(dateObj)).toBe(longUSDate(dateObj));
  });
});

/**
 * formatRange (edge cases):
 * Exercises invalid inputs and Date object support to ensure stable output.
 */
describe('formatRange (additional edge cases)', () => {
  /** Undefined start and end returns the standard fallback message. */
  it('returns "No Dates Available" when both are undefined', () => {
    expect(formatRange(undefined, undefined)).toBe('No Dates Available');
  });

  /** If start is invalid, end (if valid) should be used. */
  it('returns end date when start is invalid but end is valid', () => {
    const end = utcMidday('2024-02-15');
    expect(formatRange('not-a-date', end)).toBe(longUSDate(end));
  });

  /** If end is invalid, start (if valid) should be used. */
  it('returns start date when end is invalid but start is valid', () => {
    const start = utcMidday('2024-01-01');
    expect(formatRange(start, 'not-a-date')).toBe(longUSDate(start));
  });

  /** If both are invalid, fallback message is returned. */
  it('returns "No Dates Available" when both are invalid', () => {
    expect(formatRange('not-a-date', 'still-not-a-date')).toBe(
      'No Dates Available'
    );
  });

  /** Date objects should be accepted (and still show end-only when both exist). */
  it('accepts Date objects (still returns end-only when both provided)', () => {
    const start = new Date(utcMidday('2024-01-01'));
    const end = new Date(utcMidday('2024-01-10'));
    expect(formatRange(start, end)).toBe(longUSDate(end));
  });
});

/**
 * formatDate:
 * Validates YYYY-MM-DD formatting and documents current invalid-input behavior.
 */
describe('formatDate', () => {
  /** Null/undefined/empty inputs return an empty string. */
  it('returns empty string for null/undefined/empty', () => {
    expect(formatDate(null)).toBe('');
    expect(formatDate(undefined)).toBe('');
    expect(formatDate('')).toBe('');
  });

  /** Valid ISO strings return the YYYY-MM-DD portion. */
  it('returns YYYY-MM-DD for valid ISO date', () => {
    expect(formatDate('2024-01-15T17:45:00.000Z')).toBe('2024-01-15');
  });

  /** Timezone offsets are normalized via ISO conversion and can change the calendar date. */
  it('handles timezone offsets correctly', () => {
    expect(formatDate('2024-01-01T23:00:00-05:00')).toBe('2024-01-02');
  });

  /** Documents current behavior: invalid inputs throw due to toISOString(). */
  it('throws for invalid date input (current behavior)', () => {
    expect(() => formatDate('not-a-date')).toThrow();
  });
});

/**
 * formReadableDate:
 * Ensures machine-readable date formatting and documents invalid-input behavior.
 */
describe('formReadableDate', () => {
  /** Valid dates produce a yyyy-MM-dd HH:mm formatted string. */
  it('formats to "yyyy-MM-dd HH:mm" for valid date', () => {
    const output = formReadableDate('2024-01-15T17:45:00.000Z');
    expect(output).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
  });

  /** Documents current behavior: invalid dates throw from the formatter. */
  it('throws for invalid date input (current behavior)', () => {
    expect(() => formReadableDate('invalid-date')).toThrow();
  });
});

/**
 * humanReadableDate:
 * Ensures user-friendly timestamp formatting and documents invalid-input behavior.
 */
describe('humanReadableDate', () => {
  /** Valid dates produce a "MMM dd, yyyy hh:mm a" formatted string. */
  it('formats to "MMM dd, yyyy hh:mm a" for valid date', () => {
    const output = humanReadableDate('2024-01-15T17:45:00.000Z');
    expect(output).toMatch(/^[A-Za-z]{3} \d{2}, \d{4} \d{2}:\d{2} [AP]M$/);
  });

  /** Documents current behavior: invalid dates throw from the formatter. */
  it('throws for invalid date input (current behavior)', () => {
    expect(() => humanReadableDate('invalid-date')).toThrow();
  });
});

/**
 * toUTC / toEST:
 * Validates ET<->UTC conversions (including DST differences) and invalid input behavior.
 */
describe('toUTC / toEST', () => {
  /** Winter conversion: ET (UTC-5) -> UTC. */
  it('toUTC converts an ET local time string to UTC (winter example)', () => {
    const utc = toUTC('2024-01-15T10:30:00');
    expect(utc.startsWith('2024-01-15T15:30:00')).toBe(true);
  });

  /** Summer conversion: ET (UTC-4) -> UTC due to DST. */
  it('toUTC converts an ET local time string to UTC (summer DST example)', () => {
    const utc = toUTC('2024-06-15T10:30:00');
    expect(utc.startsWith('2024-06-15T14:30:00')).toBe(true);
  });

  /** Documents current behavior: invalid input throws in the ET->UTC conversion. */
  it('toUTC throws for invalid input (current behavior)', () => {
    expect(() => toUTC('not-a-date')).toThrow();
  });

  /** UTC -> ET conversion returns a locale string containing the expected date/time components. */
  it('toEST converts a UTC timestamp to an ET locale string', () => {
    const et = toEST('2024-01-15T15:30:00.000Z');
    expect(et).toContain('1/15/2024');
    expect(et).toMatch(/10:30/);
  });

  /** Documents current behavior: invalid input yields the literal string "Invalid Date". */
  it('toEST returns "Invalid Date" for invalid input (current behavior)', () => {
    expect(toEST('not-a-date')).toBe('Invalid Date');
  });
});
