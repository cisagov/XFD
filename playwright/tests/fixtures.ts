// tests/fixtures.ts
import { test as base, expect, Page } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';

type AxeFixture = {
  makeAxeBuilder: (page: Page) => AxeBuilder;
};

type RolePagesFixture = {
  pageAsGlobalAdmin: Page;
  pageAsRegionalAdmin: Page;
  pageAsGlobalView: Page;
  pageAsStandardUser: Page;
};

export const test = base.extend<AxeFixture & RolePagesFixture>({
  // Axe builder fixture
  makeAxeBuilder: async ({}, use) => {
    const makeAxeBuilder = (page: Page) =>
      new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .disableRules(['document-title', 'html-has-lang']); // Optional: adjust rules here
    await use(makeAxeBuilder);
  },
  // Role-based page fixtures
  pageAsGlobalAdmin: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: '.auth/global-admin.json'
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
  pageAsRegionalAdmin: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: '.auth/regional-admin.json'
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
  pageAsGlobalView: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: '.auth/global-view.json'
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
  pageAsStandardUser: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: '.auth/standard-user.json'
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  }
});
