import { describe, it, expect } from 'vitest';
import {
  isEmptyAfterScans,
  shouldSkipVulnType,
  sortByCvssThenCountDesc
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

describe('sortByCvssThenCountDesc', () => {
  it('sorts by cvss_base_score in descending order', () => {
    const input = [
      { cvss_base_score: 4.8, count: 1 },
      { cvss_base_score: 9.5, count: 1 },
      { cvss_base_score: 6.6, count: 1 }
    ];

    const result = sortByCvssThenCountDesc(input);

    expect(result.map((v) => v.cvss_base_score)).toEqual([9.5, 6.6, 4.8]);
  });

  it('uses count as a tie-breaker when cvss scores are equal', () => {
    const input = [
      { cvss_base_score: 9.0, count: 2 },
      { cvss_base_score: 9.0, count: 10 },
      { cvss_base_score: 9.0, count: 5 }
    ];

    const result = sortByCvssThenCountDesc(input);

    expect(result.map((v) => v.count)).toEqual([10, 5, 2]);
  });

  it('sorts by cvss first even if lower cvss has higher count', () => {
    const input = [
      { cvss_base_score: 8.0, count: 100 },
      { cvss_base_score: 9.0, count: 1 }
    ];

    const result = sortByCvssThenCountDesc(input);

    expect(result[0].cvss_base_score).toBe(9.0);
  });

  it('treats null or undefined cvss and count as 0', () => {
    const input = [
      { cvss_base_score: null, count: null },
      { cvss_base_score: 5.0, count: undefined },
      { cvss_base_score: undefined, count: 10 }
    ];

    const result = sortByCvssThenCountDesc(input);

    expect(result[0].cvss_base_score).toBe(5.0);
  });

  it('does not mutate the original array', () => {
    const input = [
      { cvss_base_score: 1, count: 1 },
      { cvss_base_score: 2, count: 2 }
    ];

    const original = [...input];
    sortByCvssThenCountDesc(input);

    expect(input).toEqual(original);
  });
});
