import { describe, it, expect } from 'vitest';
import {
  isEmptyAfterScans,
  shouldSkipVulnType
} from '../../utils/transformVulnScanData';

describe('isEmptyAfterScans', () => {
  it('returns false if vulnScanSummary is missing', () => {
    const data = {
      vulnScanKeyMetrics: [{ value: 0 }]
    };
    expect(isEmptyAfterScans(data)).toBe(false);
  });

  it('returns true when all metric values are 0', () => {
    const data = {
      vulnScanSummary: [{}],
      vulnScanKeyMetrics: [
        { value: 0 },
        { value: 0 },
        { value: null },
        { value: undefined }
      ]
    };
    expect(isEmptyAfterScans(data)).toBe(true);
  });

  it('returns false when any metric value is nonzero', () => {
    const data = {
      vulnScanSummary: [{}],
      vulnScanKeyMetrics: [
        { value: 0 },
        { value: 1 }, // Non-zero value should fail
        { value: 0 }
      ]
    };
    expect(isEmptyAfterScans(data)).toBe(false);
  });

  it('returns true when vulnScanKeyMetrics is missing (treated as empty array)', () => {
    const data = {
      vulnScanSummary: [{}]
    };
    expect(isEmptyAfterScans(data)).toBe(true);
  });

  it('returns true when vulnScanKeyMetrics is an empty array', () => {
    const data = {
      vulnScanSummary: [{}],
      vulnScanKeyMetrics: []
    };
    expect(isEmptyAfterScans(data)).toBe(true);
  });

  it('returns false when vulnScanSummary is empty array', () => {
    const data = {
      vulnScanSummary: [],
      vulnScanKeyMetrics: [{ value: 0 }]
    };
    expect(isEmptyAfterScans(data)).toBe(false);
  });
});

describe('shouldSkipVulnType', () => {
  const sampleData = [
    {
      vulnType: 'KEV',
      lowSeverity: 0,
      mediumSeverity: 0,
      highSeverity: 0,
      criticalSeverity: 0
    },
    {
      vulnType: 'Distinct',
      lowSeverity: 2,
      mediumSeverity: 0,
      highSeverity: 0,
      criticalSeverity: 0
    }
  ];

  it('returns true when vulnType entry is missing', () => {
    const result = shouldSkipVulnType(sampleData, 'NonexistentType');
    expect(result).toBe(true);
  });

  it('returns true when all severity values are 0', () => {
    const result = shouldSkipVulnType(sampleData, 'KEV');
    expect(result).toBe(true);
  });

  it('returns false when at least one severity value is nonzero', () => {
    const result = shouldSkipVulnType(sampleData, 'Distinct');
    expect(result).toBe(false);
  });

  it('handles empty array gracefully', () => {
    const result = shouldSkipVulnType([], 'KEV');
    expect(result).toBe(true);
  });
});
