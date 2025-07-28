const { test, expect, Page } = require('../../axe-test');
import type { TestInfo } from '@playwright/test';

test.describe('Vulnerabilities', () => {
  test('Test vulnerabilities accessibility', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await page.goto('/inventory/vulnerabilities');

    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  //TODO: Skip this test until the vulnerability table data is loaded in localhost.
  test.skip('Test vulnerability details NIST link', async ({ page }) => {
    await page.goto('/inventory/vulnerabilities');
    const newTabPromise = page.waitForEvent('popup');

    await page.getByRole('row').nth(1).getByRole('cell').nth(0).click();
    const newTab = await newTabPromise;
    await newTab.waitForLoadState();
    await expect(newTab).toHaveURL(
      new RegExp('^https://nvd\\.nist\\.gov/vuln/detail/')
    );
  });

  //TODO: Skip this test until the vulnerability table data is loaded in localhost.
  test.skip('Test domain details link', async ({ page }) => {
    await page.goto('/inventory/vulnerabilities');
    await page.getByRole('row').nth(1).getByRole('cell').nth(3).click();
    await expect(page).toHaveURL(new RegExp('/inventory/domain/'));
  });

  //TODO: Skip this test until the vulnerability table data is loaded in localhost.
  test.skip('Test vulnerability details accessibility', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await page.goto('/inventory/vulnerabilities');
    await page.getByRole('row').nth(1).getByRole('cell').nth(7).click();
    await expect(page).toHaveURL(new RegExp('/inventory/vulnerability/'));

    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });
});
