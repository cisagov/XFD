import { describe, expect, it } from 'vitest';
import { cleanFilterModelItems } from '@/utils/tableUtils';

describe('cleanFilterModelItems', () => {
  it('clears value when field changes then filters them out', () => {
    const newModel = {
      items: [{ id: 1, field: 'name', operator: 'equals', value: 'test' }]
    };
    const previousModel = {
      items: [
        { id: 1, field: 'severity', operator: 'equals', value: 'oldValue' }
      ]
    };

    const cleanedModel = cleanFilterModelItems(newModel, previousModel);
    expect(cleanedModel.items.length).toBe(0);
  });

  it('normalizes empty/null/whitespace values to undefined then filters them out', () => {
    const newModel = {
      items: [{ id: 1, field: 'name', operator: 'equals', value: '' }]
    };
    const previousModel = {
      items: [{ id: 1, field: 'name', operator: 'equals', value: 'oldValue' }]
    };

    const cleanedModel = cleanFilterModelItems(newModel, previousModel);
    expect(cleanedModel.items.length).toBe(0);
  });
});
