import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import type { TestInfo } from '@playwright/test';

test.describe('Inventory', () => {
  test.skip('Test inventory accessibility', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await pageAsGlobalAdmin.goto('/inventory');
    const accessibilityScanResults =
      await makeAxeBuilder(pageAsGlobalAdmin).analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  test.skip('Test domain accessibility', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await pageAsGlobalAdmin.goto('/inventory/domains');
    const accessibilityScanResults =
      await makeAxeBuilder(pageAsGlobalAdmin).analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  // TODO: Skip this test until the domain table data is loaded in localhost.
  test.skip('Test domain details accessibility', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await pageAsGlobalAdmin.goto('/inventory/domains');
    await pageAsGlobalAdmin
      .getByRole('row')
      .nth(1)
      .getByRole('cell')
      .nth(8)
      .getByRole('button')
      .click();
    await expect(pageAsGlobalAdmin).toHaveURL(
      new RegExp('/inventory/domain/'),
      {
        timeout: 10000
      }
    );

    const accessibilityScanResults =
      await makeAxeBuilder(pageAsGlobalAdmin).analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  // TODO: Skip this test until the domain table data is loaded in localhost.
  test.skip('Test domain table filter', async ({ pageAsGlobalAdmin }) => {
    await pageAsGlobalAdmin.goto('/inventory/domains');
    await pageAsGlobalAdmin.getByLabel('Show filters').click();
    await pageAsGlobalAdmin.getByPlaceholder('Filter value').click();
    await pageAsGlobalAdmin.getByPlaceholder('Filter value').fill('Homeland');
    await pageAsGlobalAdmin.getByPlaceholder('Filter value').press('Enter');

    let rowCount = await pageAsGlobalAdmin.getByRole('row').count();
    for (let it = 2; it < rowCount; it++) {
      await expect(
        pageAsGlobalAdmin.getByRole('row').nth(it).getByRole('cell').nth(0)
      ).toContainText('Homeland');
    }
  });
});
