const { test, expect } = require('../../axe-test');
import type { TestInfo } from '@playwright/test';

test.describe('Inventory', () => {
  test('Test inventory accessibility', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await page.goto('/inventory');
    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  test('Test domain accessibility', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await page.goto('/inventory/domains');
    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  // TODO: Skip this test until the domain table data is loaded in localhost.
  test.skip('Test domain details accessibility', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await page.goto('/inventory/domains');
    await page
      .getByRole('row')
      .nth(1)
      .getByRole('cell')
      .nth(8)
      .getByRole('button')
      .click();
    await expect(page).toHaveURL(new RegExp('/inventory/domain/'), {
      timeout: 10000
    });

    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  // TODO: Skip this test until the domain table data is loaded in localhost.
  test.skip('Test domain table filter', async ({ page }) => {
    await page.goto('/inventory/domains');
    await page.getByLabel('Show filters').click();
    await page.getByPlaceholder('Filter value').click();
    await page.getByPlaceholder('Filter value').fill('Homeland');
    await page.getByPlaceholder('Filter value').press('Enter');

    let rowCount = await page.getByRole('row').count();
    for (let it = 2; it < rowCount; it++) {
      await expect(
        page.getByRole('row').nth(it).getByRole('cell').nth(0)
      ).toContainText('Homeland');
    }
  });
});
