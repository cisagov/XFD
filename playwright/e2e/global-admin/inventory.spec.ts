import { describe } from 'node:test';

const { test, expect, Page } = require('../../axe-test');

test.describe.configure({ mode: 'parallel' });
let page: InstanceType<typeof Page>;

test.describe('Inventory', () => {
  test.beforeEach(async ({ browser }) => {
    const context = await browser.newContext();
    page = await context.newPage();
    await page.goto('/');
  });

  test.afterEach(async () => {
    await page.close();
  });
  test('Test inventory accessibility', async ({ makeAxeBuilder }, testInfo) => {
    await page.getByRole('link', { name: 'Inventory' }).click();
    await expect(page).toHaveURL('/inventory');

    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toEqual([]);

    await page.screenshot({
      path: 'test-results/img/global-admin/inventory.png'
    });
  });

  test('Test domain accessibility', async ({ makeAxeBuilder }, testInfo) => {
    await page.goto('/inventory');
    await page.getByRole('link', { name: 'All Domains' }).click();
    await expect(page).toHaveURL('/inventory/domains');

    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toEqual([]);

    await page.screenshot({
      path: 'test-results/img/global-admin/domains.png'
    });
  });

  test('Test domain details accessibility', async ({
    makeAxeBuilder
  }, testInfo) => {
    await page.goto('/inventory/domains');
    await page
      .getByRole('row')
      .nth(1)
      .getByRole('cell')
      .nth(8)
      .getByRole('button')
      .click();
    await expect(page).toHaveURL(new RegExp('/inventory/domain/'));

    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toEqual([]);

    await page.screenshot({
      path: 'test-results/img/global-admin/domain_details.png'
    });
  });

  test('Test domain table filter', async () => {
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
    await page.screenshot({
      path: 'test-results/img/global-admin/domain_filter.png'
    });
  });
});
