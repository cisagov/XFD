import { describe, expect, it } from 'vitest';
import { buildOrgFilters } from '@/utils/tableUtils';

describe('buildOrgFilters', () => {
  describe('builds filters object correctly from filter model', () => {
    it('builds name object correctly from filter model', () => {
      const model = {
        items: [{ field: 'name', operator: 'contains', value: 'Test' }]
      };
      const filters = buildOrgFilters(model);
      expect(filters).toEqual({
        name: 'Test'
      });
    });

    it('builds acronym object correctly from filter model', () => {
      const model = {
        items: [{ field: 'acronym', operator: 'equals', value: 'XYZ' }]
      };
      const filters = buildOrgFilters(model);
      expect(filters).toEqual({
        acronym: 'XYZ'
      });
    });

    it('builds state object correctly from filter model', () => {
      const model = {
        items: [{ field: 'state', operator: 'equals', value: 'active' }]
      };
      const filters = buildOrgFilters(model);
      expect(filters).toEqual({
        state: 'active'
      });
    });

    it('builds region_id object correctly from filter model', () => {
      const model = {
        items: [{ field: 'region_id', operator: 'equals', value: '1' }]
      };
      const filters = buildOrgFilters(model);
      expect(filters).toEqual({
        region_id: '1'
      });
    });
  });

  it('handles empty filter model', () => {
    const model = { items: [] };
    const filters = buildOrgFilters(model);
    expect(filters).toEqual({});
  });

  it('handles missing values', () => {
    const model = {
      items: [{ field: 'name', operator: 'contains', value: undefined }]
    };
    const filters = buildOrgFilters(model);
    expect(filters).toEqual({});
  });

  it('ignores empty string values', () => {
    const model = {
      items: [{ field: 'name', operator: 'contains', value: '' }]
    };
    const filters = buildOrgFilters(model);
    expect(filters).toEqual({});
  });

  it('trims whitespace from filter values', () => {
    const model = {
      items: [{ field: 'name', operator: 'contains', value: '  Test  ' }]
    };
    const filters = buildOrgFilters(model);
    expect(filters).toEqual({
      name: 'Test'
    });
  });
});
