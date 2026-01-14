import { describe, it, expect } from 'vitest';
import {
  capitalize,
  formatDisplayValue,
  matchPath,
  truncateString
} from '@/utils/stringUtils';

describe('capitalize', () => {
  it('capitalizes the first letter of a string', () => {
    expect(capitalize('hello')).toBe('Hello');
  });

  it('returns the same string if already capitalized', () => {
    expect(capitalize('Hello')).toBe('Hello');
  });

  it('returns an empty string if input is empty', () => {
    expect(capitalize('')).toBe('');
  });

  it('returns null if input is null', () => {
    expect(capitalize(null)).toBeNull();
  });
});

describe('formatDisplayValue', () => {
  it('formats numbers with commas', () => {
    expect(formatDisplayValue(1000)).toBe('1,000');
    expect(formatDisplayValue(3071)).toBe('3,071');
  });

  it('formats zero correctly', () => {
    expect(formatDisplayValue(0)).toBe('0');
  });

  it('returns strings unchanged', () => {
    expect(formatDisplayValue('test')).toBe('test');
  });

  it('returns null unchanged', () => {
    expect(formatDisplayValue(null)).toBeNull();
  });

  it('returns undefined unchanged', () => {
    expect(formatDisplayValue(undefined)).toBeUndefined();
  });
});

describe('matchPath', () => {
  it('returns true when path exists in paths array', () => {
    expect(matchPath(['/home', '/about'], '/home')).toBe(true);
  });

  it('returns false when path does not exist in paths array', () => {
    expect(matchPath(['/home', '/about'], '/contact')).toBe(false);
  });

  it('returns false when paths array is empty', () => {
    expect(matchPath([], '/home')).toBe(false);
  });
});

describe('truncateString', () => {
  it('returns the full string when no truncation markers exist', () => {
    expect(truncateString('Example Service Name')).toBe('Example Service Name');
  });

  it('truncates at the first occurrence of " ("', () => {
    expect(truncateString('Service Name (v1.2)')).toBe('Service Name');
  });

  it('truncates at the first occurrence of " at"', () => {
    expect(truncateString('Service Name at Location')).toBe('Service Name');
  });

  it('truncates at the earliest occurrence when both markers exist', () => {
    expect(truncateString('Service Name (v1.2) at Location')).toBe(
      'Service Name'
    );
  });
});
