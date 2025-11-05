import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { Domains } from '../../pages/Domains/Domains';

describe('Domains component', () => {
  it('is exported', () => {
    expect(Domains).toBeDefined();
    // functional components are functions, class components are functions/objects
    expect(['function', 'object']).toContain(typeof Domains);
  });

  const apiPostMock = vi.fn().mockResolvedValue({ result: [], count: 0 });

  beforeEach(() => {
    apiPostMock.mockClear();
  });

  it('matches snapshot', () => {
    const domainComponent = <Domains />;
    expect(domainComponent).toMatchSnapshot();
  });
});
