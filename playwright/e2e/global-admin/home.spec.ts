import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import type { Page, TestInfo } from '@playwright/test';

test.describe('Home Page Accessibility', () => {
  test('Global Admin: homepage accessibility', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await runAccessibilityTest(
      pageAsGlobalAdmin,
      makeAxeBuilder,
      testInfo,
      'Global Admin'
    );
  });
  test('Regional Admin: homepage accessibility', async ({
    pageAsRegionalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await runAccessibilityTest(
      pageAsRegionalAdmin,
      makeAxeBuilder,
      testInfo,
      'Regional Admin'
    );
  });
  test('Global View: homepage accessibility', async ({
    pageAsGlobalView,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await runAccessibilityTest(
      pageAsGlobalView,
      makeAxeBuilder,
      testInfo,
      'Global View'
    );
  });
  test('Standard User: homepage accessibility', async ({
    pageAsStandardUser,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await runAccessibilityTest(
      pageAsStandardUser,
      makeAxeBuilder,
      testInfo,
      'Standard User'
    );
  });
});

// Extracted helper function
async function runAccessibilityTest(
  page: Page,
  makeAxeBuilder: (page: Page) => any,
  testInfo: TestInfo,
  role: string
) {
  await page.goto('/');

  const axe = makeAxeBuilder(page);
  const results = await axe.analyze();

  await testInfo.attach(`${role} - accessibility-scan-results`, {
    body: JSON.stringify(results, null, 2),
    contentType: 'application/json'
  });

  expect(results.violations).toHaveLength(0);
}
