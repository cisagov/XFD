import { describe, expect, it, vi } from 'vitest';
import type { GridFilterItem, GridFilterModel } from '@mui/x-data-grid';

import {
  cleanFilterModelItems,
  convertStringToBooleanValue,
  extractInitialFilters,
  formatSeverity,
  normalizeFilters,
  shouldTriggerFilterUpdate
} from '@/utils/vulnerabilitiesTableUtils';

vi.mock('hooks/useUserTypeFilters', () => ({
  ORGANIZATION_EXCLUSIONS: ['excluded']
}));

type MinimalLocationState = Record<string, unknown>;

/**
 * vulnerabilitiesTableUtils:
 * Validates severity formatting, filter extraction, normalization rules, and update detection logic
 * for the vulnerabilities table utilities.
 */
describe('vulnerabilitiesTableUtils', () => {
  /**
   * formatSeverity:
   * Normalizes raw severity inputs into the canonical UI severity labels.
   */
  describe('formatSeverity', () => {
    /** Formats known severity levels with correct title-casing (case-insensitive). */
    it('returns correct formatting for known severity levels (case-insensitive)', () => {
      expect(formatSeverity('low')).toBe('Low');
      expect(formatSeverity('MEDIUM')).toBe('Medium');
      expect(formatSeverity('High')).toBe('High');
      expect(formatSeverity('critical')).toBe('Critical');
      expect(formatSeverity('Other')).toBe('Other');
      expect(formatSeverity('N/A')).toBe('N/A');
    });

    /** Returns N/A for well-known empty markers; whitespace becomes Other (current behavior). */
    it('returns N/A for known empty markers, but whitespace becomes Other (current behavior)', () => {
      expect(formatSeverity('None')).toBe('N/A');
      expect(formatSeverity('Null')).toBe('N/A');
      expect(formatSeverity('Undefined')).toBe('N/A');
      expect(formatSeverity('undefined')).toBe('N/A');
      expect(formatSeverity('')).toBe('N/A');

      // Current implementation does not trim before checking empty, so whitespace becomes "Other".
      expect(formatSeverity('   ')).toBe('Other');

      expect(formatSeverity('n/a')).toBe('N/A');
      expect(formatSeverity('N/a')).toBe('N/A');
    });

    /** Returns Other for any unrecognized severity string. */
    it('returns Other for unrecognized severity strings', () => {
      expect(formatSeverity('Severe')).toBe('Other');
      expect(formatSeverity('Informational')).toBe('Other');
      expect(formatSeverity('WEIRD')).toBe('Other');
    });

    /** Documents current behavior: non-string inputs throw due to string operations in titleCase(). */
    it('throws for non-string / missing input (current behavior)', () => {
      expect(() => formatSeverity(undefined)).toThrow();
      expect(() => formatSeverity(null as any)).toThrow();
      expect(() => formatSeverity(12345 as any)).toThrow();
      expect(() => formatSeverity({ value: 'low' } as any)).toThrow();
    });
  });

  /**
   * convertStringToBooleanValue:
   * Converts KEV-related string inputs ("yes"/"no"/"true"/"false") into booleans/null.
   */
  describe('convertStringToBooleanValue', () => {
    /** Converts recognized yes/no/true/false strings for KEV fields into booleans. */
    it('converts is_kev and is_kev_ransomware string values to booleans', () => {
      expect(convertStringToBooleanValue('is_kev', 'yes')).toBe(true);
      expect(convertStringToBooleanValue('is_kev', 'TRUE')).toBe(true);
      expect(convertStringToBooleanValue('is_kev', 'no')).toBe(false);
      expect(convertStringToBooleanValue('is_kev', 'false')).toBe(false);

      expect(convertStringToBooleanValue('is_kev_ransomware', 'yes')).toBe(
        true
      );
      expect(convertStringToBooleanValue('is_kev_ransomware', 'true')).toBe(
        true
      );
      expect(convertStringToBooleanValue('is_kev_ransomware', 'no')).toBe(
        false
      );
      expect(convertStringToBooleanValue('is_kev_ransomware', 'FALSE')).toBe(
        false
      );
    });

    /** Returns null for unrecognized boolean-like strings for KEV fields. */
    it('returns null for unknown boolean-like strings', () => {
      expect(convertStringToBooleanValue('is_kev', 'maybe')).toBe(null);
      expect(convertStringToBooleanValue('is_kev_ransomware', 'unknown')).toBe(
        null
      );
    });

    /** Does not convert non-KEV fields (pass-through behavior). */
    it('does not convert non-target fields', () => {
      expect(convertStringToBooleanValue('severity', 'yes')).toBe('yes');
      expect(convertStringToBooleanValue('organization', 'true')).toBe('true');
      expect(convertStringToBooleanValue('title', 'no')).toBe('no');
    });

    /** Leaves non-string values unchanged for KEV fields. */
    it('does not convert non-string values for target fields', () => {
      expect(convertStringToBooleanValue('is_kev', true)).toBe(true);
      expect(convertStringToBooleanValue('is_kev', false)).toBe(false);
      expect(convertStringToBooleanValue('is_kev', null)).toBe(null);
      expect(convertStringToBooleanValue('is_kev_ransomware', true)).toBe(true);
    });
  });

  /**
   * extractInitialFilters:
   * Converts location state inputs into hidden DataGrid filter items.
   */
  describe('extractInitialFilters', () => {
    /** Builds the expected filter items when all supported state properties are present. */
    it('derives filters from location state (all supported fields)', () => {
      const state: MinimalLocationState = {
        title: 'openssl',
        domain: 'example.com',
        severity: 'high',
        kev: 'yes',
        orgId: 'org-123',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
        dateRange: 'last_30_days',
        scanType: 'vs'
      };

      const filters = extractInitialFilters(state as any);

      expect(filters).toEqual([
        { field: 'title', value: 'openssl', operator: 'contains' },
        { field: 'domain', value: 'example.com', operator: 'contains' },
        { field: 'severity', value: 'high', operator: 'contains' },
        { field: 'is_kev', value: 'yes', operator: 'equals' },
        { field: 'organization', value: 'org-123', operator: 'equals' },
        { field: 'earliest_date', value: '2024-01-01', operator: 'equals' },
        { field: 'latest_date', value: '2024-01-31', operator: 'equals' },
        { field: 'date_range', value: 'last_30_days', operator: 'equals' },
        { field: 'scan_type', value: 'vs', operator: 'equals' }
      ]);
    });

    /** Only creates filters for fields present in the input state. */
    it('derives only the filters present (partial input)', () => {
      const state: MinimalLocationState = {
        title: 'openssl',
        orgId: 'org-123'
      };

      const filters = extractInitialFilters(state as any);

      expect(filters).toEqual([
        { field: 'title', value: 'openssl', operator: 'contains' },
        { field: 'organization', value: 'org-123', operator: 'equals' }
      ]);
    });

    /** Missing/empty state produces no initial filters. */
    it('returns an empty array when state is missing or empty', () => {
      expect(extractInitialFilters(undefined as any)).toEqual([]);
      expect(extractInitialFilters(null as any)).toEqual([]);
      expect(extractInitialFilters({} as any)).toEqual([]);
    });

    /** Unsupported keys are ignored. */
    it('ignores unsupported fields in state', () => {
      const state: MinimalLocationState = {
        randomField: 'nope',
        another: 123
      };
      expect(extractInitialFilters(state as any)).toEqual([]);
    });

    /** Documents current behavior: kev=false does not produce an is_kev filter because it is falsy. */
    it('audit: does not include kev filter when kev is false (current behavior)', () => {
      const state: MinimalLocationState = { kev: false };
      expect(extractInitialFilters(state as any)).toEqual([]);
    });
  });

  /**
   * normalizeFilters:
   * Transforms DataGrid filter items into a normalized record used by API/query logic.
   */
  describe('normalizeFilters', () => {
    /** Drops filter items with undefined/null/empty/whitespace string values. */
    it('filters out undefined/null/empty/whitespace filter values', () => {
      const filters: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any,
        { field: 'domain', operator: 'contains', value: '' } as any,
        { field: 'severity', operator: 'contains', value: '   ' } as any,
        { field: 'is_kev', operator: 'equals', value: null } as any,
        { field: 'scan_type', operator: 'equals', value: undefined } as any
      ];

      const normalized = normalizeFilters(filters, null, 'standard');
      expect(normalized).toEqual({ title: 'openssl' });
    });

    /** Ensures falsy-but-valid values (false, 0) are retained for non-KEV fields. */
    it('keeps boolean/number values (non-empty) as-is for non-KEV fields', () => {
      const normalizedFalse = normalizeFilters(
        [{ field: 'someField', operator: 'equals', value: false } as any],
        null,
        'standard'
      );
      expect(normalizedFalse).toEqual({ someField: false });

      const normalizedZero = normalizeFilters(
        [{ field: 'count', operator: 'equals', value: 0 } as any],
        null,
        'standard'
      );
      expect(normalizedZero).toEqual({ count: 0 });
    });

    /** Converts KEV string values into booleans/null using convertStringToBooleanValue. */
    it('converts is_kev and is_kev_ransomware to boolean/null', () => {
      const filters: GridFilterItem[] = [
        { field: 'is_kev', operator: 'equals', value: 'YES' } as any,
        {
          field: 'is_kev_ransomware',
          operator: 'equals',
          value: 'maybe'
        } as any
      ];

      const normalized = normalizeFilters(filters, null, 'standard');

      expect(normalized).toEqual({
        is_kev: true,
        is_kev_ransomware: null
      });
    });

    /** Normalizes severity values using formatSeverity. */
    it('formats severity via formatSeverity', () => {
      const filters: GridFilterItem[] = [
        { field: 'severity', operator: 'contains', value: 'critical' } as any
      ];

      const normalized = normalizeFilters(filters, null, 'standard');
      expect(normalized).toEqual({ severity: 'Critical' });
    });

    /** Documents current behavior: a truthy non-string severity triggers a throw from formatSeverity. */
    it('throws when severity is truthy but non-string (current behavior audit)', () => {
      const filters: GridFilterItem[] = [
        { field: 'severity', operator: 'contains', value: 123 } as any
      ];
      expect(() => normalizeFilters(filters, null, 'standard')).toThrow();
    });

    /** Standard users get an organization enforced from currentOrganization when not excluded. */
    it('adds organization for standard users when current org is not excluded', () => {
      const filters: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      const currentOrganization = { id: 'org-abc', name: 'Good Org' } as any;

      const normalized = normalizeFilters(
        filters,
        currentOrganization,
        'standard'
      );

      expect(normalized).toEqual({
        title: 'openssl',
        organization: 'org-abc'
      });
    });

    /** Non-standard users do not get an organization forced from currentOrganization. */
    it('does not add organization when userType is not standard', () => {
      const filters: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      const currentOrganization = { id: 'org-abc', name: 'Good Org' } as any;

      const normalized = normalizeFilters(
        filters,
        currentOrganization,
        'regional_admin'
      );

      expect(normalized).toEqual({
        title: 'openssl'
      });
    });

    /** Excluded org names should not be forced into the result for standard users. */
    it('does not add organization when org is excluded', () => {
      const filters: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      const excludedOrganization = {
        id: 'org-exc',
        name: 'This is Excluded'
      } as any;

      const normalized = normalizeFilters(
        filters,
        excludedOrganization,
        'standard'
      );

      expect(normalized).toEqual({ title: 'openssl' });
    });

    /** orgId argument should override any existing or injected organization value. */
    it('orgId argument overrides any derived organization', () => {
      const filters: GridFilterItem[] = [
        {
          field: 'organization',
          operator: 'equals',
          value: 'org-from-filter'
        } as any
      ];

      const currentOrganization = {
        id: 'org-from-user',
        name: 'Good Org'
      } as any;

      const normalized = normalizeFilters(
        filters,
        currentOrganization,
        'standard',
        'org-from-param'
      );

      expect(normalized.organization).toBe('org-from-param');
    });

    /** State values of "open"/"closed" are preserved as state (no substate extraction). */
    it('keeps state when it is exactly open/closed (no substate extraction)', () => {
      const openFilters: GridFilterItem[] = [
        { field: 'state', operator: 'equals', value: 'open' } as any
      ];
      expect(normalizeFilters(openFilters, null, 'standard')).toEqual({
        state: 'open'
      });

      const closedFilters: GridFilterItem[] = [
        { field: 'state', operator: 'equals', value: 'closed' } as any
      ];
      expect(normalizeFilters(closedFilters, null, 'standard')).toEqual({
        state: 'closed'
      });
    });

    /** Non-open/closed states with parentheses extract a normalized substate and drop state. */
    it('extracts substate from state values containing parentheses and removes state', () => {
      const filters: GridFilterItem[] = [
        {
          field: 'state',
          operator: 'equals',
          value: 'Open (In Progress)'
        } as any
      ];

      const normalized = normalizeFilters(filters, null, 'standard');
      expect(normalized).toEqual({ substate: 'in-progress' });
    });

    /** Non-open/closed states without parentheses remain as state. */
    it('keeps state when not open/closed and no parentheses exist', () => {
      const filters: GridFilterItem[] = [
        { field: 'state', operator: 'equals', value: 'In Progress' } as any
      ];

      const normalized = normalizeFilters(filters, null, 'standard');
      expect(normalized).toEqual({ state: 'In Progress' });
    });

    /** If the same field appears multiple times, the last value wins (reduce overwrite behavior). */
    it('uses the last value when multiple filter items share the same field', () => {
      const filters: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any,
        { field: 'title', operator: 'contains', value: 'nginx' } as any
      ];

      const normalized = normalizeFilters(filters, null, 'standard');
      expect(normalized).toEqual({ title: 'nginx' });
    });

    /** Documents current behavior: missing/empty fields become "undefined" or "" keys in the result. */
    it('includes malformed filter items as keys (current behavior)', () => {
      const filters = [
        { operator: 'contains', value: 'openssl' }, // missing field
        { field: '', operator: 'contains', value: 'something' } // empty field
      ] as any as GridFilterItem[];

      const normalized = normalizeFilters(filters, null, 'standard');

      expect(normalized['undefined']).toBe('openssl');
      expect(normalized['']).toBe('something');
    });

    /** Documents current behavior: non-string org.name triggers a throw during exclusion check. */
    it('throws when currentOrganization.name is non-string (current behavior audit)', () => {
      const filters: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      const badOrg = { id: 'org-abc', name: null } as any;

      expect(() => normalizeFilters(filters, badOrg, 'standard')).toThrow();
    });
  });

  /**
   * shouldTriggerFilterUpdate:
   * Determines whether the filter model change should trigger a query refresh.
   */
  describe('shouldTriggerFilterUpdate', () => {
    /** Prevents updates during intermediate state where fields exist but values are cleared. */
    it('returns false for intermediate state where previous had complete filters but new has incomplete items', () => {
      const previousItems: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      const newItems: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: '' } as any
      ];

      expect(shouldTriggerFilterUpdate(newItems, previousItems)).toBe(false);
    });

    /** Triggers when the number of complete filters changes. */
    it('returns true when filter count changes', () => {
      const previousItems: GridFilterItem[] = [];
      const newItems: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      expect(shouldTriggerFilterUpdate(newItems, previousItems)).toBe(true);
    });

    /** Triggers when any filter item differs by field/operator/value. */
    it('returns true when a filter differs (field/operator/value)', () => {
      const previousItems: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      const newItems: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'nginx' } as any
      ];

      expect(shouldTriggerFilterUpdate(newItems, previousItems)).toBe(true);
    });

    /** Does not trigger when the complete filters are identical. */
    it('returns false when complete filters are identical', () => {
      const previousItems: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      const newItems: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      expect(shouldTriggerFilterUpdate(newItems, previousItems)).toBe(false);
    });

    /** Documents current behavior: ordering differences are treated as changes due to index-based comparison. */
    it('treats reordering as a change because it compares by index (current behavior)', () => {
      const previousItems: GridFilterItem[] = [
        { field: 'title', operator: 'contains', value: 'openssl' } as any,
        { field: 'domain', operator: 'contains', value: 'example.com' } as any
      ];

      const newItems: GridFilterItem[] = [
        { field: 'domain', operator: 'contains', value: 'example.com' } as any,
        { field: 'title', operator: 'contains', value: 'openssl' } as any
      ];

      expect(shouldTriggerFilterUpdate(newItems, previousItems)).toBe(true);
    });
  });

  /**
   * cleanFilterModelItems:
   * Clears carried-over values when fields change and normalizes empty values to undefined.
   */
  describe('cleanFilterModelItems', () => {
    /** Clears the value when the field changes but the id remains the same (prevents carryover). */
    it('clears value when field changes for the same filter id', () => {
      const previousModel: GridFilterModel = {
        items: [
          {
            id: 1,
            field: 'title',
            operator: 'contains',
            value: 'openssl'
          } as any
        ]
      };

      const newModel: GridFilterModel = {
        items: [
          {
            id: 1,
            field: 'domain',
            operator: 'contains',
            value: 'example.com'
          } as any
        ]
      };

      const cleaned = cleanFilterModelItems(newModel, previousModel);

      expect(cleaned.items[0].value).toBe(undefined);
    });

    /** Does not clear the value when the id changes (treated as a new item). */
    it('does not clear value when field changes but id is different', () => {
      const previousModel: GridFilterModel = {
        items: [
          {
            id: 1,
            field: 'title',
            operator: 'contains',
            value: 'openssl'
          } as any
        ]
      };

      const newModel: GridFilterModel = {
        items: [
          {
            id: 2,
            field: 'domain',
            operator: 'contains',
            value: 'example.com'
          } as any
        ]
      };

      const cleaned = cleanFilterModelItems(newModel, previousModel);

      expect(cleaned.items[0].value).toBe('example.com');
    });

    /** Normalizes empty/null/whitespace values to undefined for consistent "empty" semantics. */
    it('normalizes empty/null/whitespace values to undefined', () => {
      const previousModel: GridFilterModel = {
        items: [
          {
            id: 1,
            field: 'title',
            operator: 'contains',
            value: 'openssl'
          } as any,
          {
            id: 2,
            field: 'domain',
            operator: 'contains',
            value: 'example.com'
          } as any,
          {
            id: 3,
            field: 'severity',
            operator: 'contains',
            value: 'high'
          } as any
        ]
      };

      const newModel: GridFilterModel = {
        items: [
          { id: 1, field: 'title', operator: 'contains', value: '' } as any,
          { id: 2, field: 'domain', operator: 'contains', value: null } as any,
          {
            id: 3,
            field: 'severity',
            operator: 'contains',
            value: '   '
          } as any
        ]
      };

      const cleaned = cleanFilterModelItems(newModel, previousModel);

      expect(cleaned.items.map((item) => item.value)).toEqual([
        undefined,
        undefined,
        undefined
      ]);
    });

    /** Valid values remain unchanged. */
    it('leaves valid values untouched', () => {
      const previousModel: GridFilterModel = {
        items: [
          {
            id: 1,
            field: 'title',
            operator: 'contains',
            value: 'openssl'
          } as any
        ]
      };

      const newModel: GridFilterModel = {
        items: [
          { id: 1, field: 'title', operator: 'contains', value: 'nginx' } as any
        ]
      };

      const cleaned = cleanFilterModelItems(newModel, previousModel);

      expect(cleaned.items[0].value).toBe('nginx');
    });
  });
});
