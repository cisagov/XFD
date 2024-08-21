const { test, expect, Page } = require('../../axe-test');

test.describe.configure({ mode: 'parallel' });
let page: InstanceType<typeof Page>;

test.describe('Vulnerabilities', () => {
  test.beforeEach(async ({ browser }) => {
    const context = await browser.newContext();
    page = await context.newPage();
    await page.goto('/');
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('Test vulnerabilities accessibility', async ({
    makeAxeBuilder
  }, testInfo) => {
    await page.getByRole('link', { name: 'Inventory' }).click();
    await page.getByRole('link', { name: 'All Vulnerabilities' }).click();
    await expect(page).toHaveURL('/inventory/vulnerabilities');

    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  test('Test vulnerability details NIST link', async () => {
    await page.goto('/inventory/vulnerabilities');
    const newTabPromise = page.waitForEvent('popup');

    await page.getByRole('row').nth(1).getByRole('cell').nth(0).click();
    const newTab = await newTabPromise;
    await newTab.waitForLoadState();
    await expect(newTab).toHaveURL(
      new RegExp('^https://nvd\\.nist\\.gov/vuln/detail/')
    );
  });

  test('Test domain details link', async () => {
    await page.goto('/inventory/vulnerabilities');
    await page.getByRole('row').nth(1).getByRole('cell').nth(3).click();
    await expect(page).toHaveURL(new RegExp('/inventory/domain/'));
  });

  test('Test vulnerability details accessibility', async ({
    makeAxeBuilder
  }, testInfo) => {
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
