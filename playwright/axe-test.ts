import { test as base, defineConfig } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { describe } from 'node:test';
import { configure } from 'axe-core';

type AxeFixture = {
  makeAxeBuilder: () => AxeBuilder;
};

// Extend base test by providing "makeAxeBuilder"
//
// This new "test" can be used in multiple test files, and each of them will get
// a consistently configured AxeBuilder instance.
export const test = base.extend<AxeFixture>({
  makeAxeBuilder: async ({ page }, use, testInfo) => {
    const makeAxeBuilder = () =>
      new AxeBuilder({ page }).withTags([
        'wcag2a',
        'wcag2aa',
        'wcag21a',
        'wcag21aa'
      ]);
    await use(makeAxeBuilder);
  }
});
export { expect } from '@playwright/test';
export { Page } from '@playwright/test';
