import { describe, expect, it } from 'vitest';
import { shouldTriggerFilterUpdate } from '@/utils/tableUtils';

describe('shouldTriggerFilterUpdate', () => {
  it('returns true when previous and current filter models are different', () => {
    const prevModel = {
      field: 'severity',
      operator: 'equals',
      value: 'high'
    };
    const newModel = {
      field: 'severity',
      operator: 'equals',
      value: 'medium'
    };

    const result = shouldTriggerFilterUpdate([newModel], [prevModel]);
    expect(result).toBe(true);
  });

  it('returns false when previous and current filter models are the same', () => {
    const prevModel = {
      field: 'severity',
      operator: 'equals',
      value: 'high'
    };
    const newModel = {
      field: 'severity',
      operator: 'equals',
      value: 'high'
    };

    const result = shouldTriggerFilterUpdate([newModel], [prevModel]);
    expect(result).toBe(false);
  });

  it('returns true when transitioning from previous filter value to deleted value', () => {
    const prevModel = [
      {
        field: 'severity',
        operator: 'equals',
        value: 'high'
      }
    ];
    const newModel = [
      {
        field: 'severity',
        operator: 'equals',
        value: ''
      }
    ];

    const result = shouldTriggerFilterUpdate(newModel, prevModel);
    expect(result).toBe(true);
  });

  it('returns true when transitioning from no filters to filters', () => {
    const prevModel: any[] = [];
    const newModel = [
      {
        field: 'severity',
        operator: 'equals',
        value: 'high'
      }
    ];

    const result = shouldTriggerFilterUpdate(newModel, prevModel);
    expect(result).toBe(true);
  });
});
