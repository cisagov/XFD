import { describe, expect, it } from 'vitest';
import { cleanFilterModelItems } from '@/utils/tableUtils';

describe('cleanFilterModelItems', () => {
  it('clears value when field changes and sets it to undefined', () => {
    const newModel = {
      items: [{ id: 1, field: 'name', operator: 'equals', value: 'test' }]
    };
    const previousModel = {
      items: [
        { id: 1, field: 'severity', operator: 'equals', value: 'oldValue' }
      ]
    };

    const cleanedModel = cleanFilterModelItems(newModel, previousModel);
    expect(cleanedModel.items[0].value).toBeUndefined();
  });

  it('normalizes empty/null/whitespace values to undefined', () => {
    const newModel = {
      items: [{ id: 1, field: 'name', operator: 'equals', value: '' }]
    };
    const previousModel = {
      items: [{ id: 1, field: 'name', operator: 'equals', value: 'oldValue' }]
    };

    const cleanedModel = cleanFilterModelItems(newModel, previousModel);
    expect(cleanedModel.items[0].value).toBeUndefined();
  });
});
