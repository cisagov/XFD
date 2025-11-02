import React from 'react';
import { render } from 'test-utils';
import { SearchBar } from '../FilterDrawer/SearchBar';
import { expect, it, vi } from 'vitest';

it('matches snapshot', () => {
  const { asFragment } = render(
    <SearchBar
      onChange={vi.fn()}
      autocompletedResults={[]}
      onSelectResult={vi.fn()}
      initialValue={'test'}
    />
  );
  expect(asFragment()).toMatchSnapshot();
});
