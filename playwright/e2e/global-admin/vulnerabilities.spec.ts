import { test, expect, chromium, Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });
let page: Page;

test.beforeAll(async ({ browser }) => {
  page = await browser.newPage();
  await page.goto('/');
});

test.afterAll(async () => {
  await page.close();
});

test('Vulnerabilities', async () => {
  await page.getByRole('link', { name: 'Inventory' }).click();
  await page.getByRole('link', { name: 'All Vulnerabilities' }).click();
  await expect(page).toHaveURL('/inventory/vulnerabilities');
  if ((await page.getByLabel('Go to next page').isDisabled()) == false) {
    await page.getByLabel('Go to next page').click();
  }
  if ((await page.getByLabel('Go to previous page').isDisabled()) == false) {
    await page.getByLabel('Go to previous page').click();
  }
  await page.screenshot({
    path: 'test-results/img/global-admin/vulnerabilities.png'
  });
});

test('Vulnerability details NIST', async () => {
  await page.goto('/inventory/vulnerabilities');
  const newTabPromise = page.waitForEvent('popup');
  await page.getByRole('row').nth(2).getByRole('link').nth(0).click();
  const newTab = await newTabPromise;
  await newTab.waitForLoadState();
  await expect(newTab).toHaveURL(
    new RegExp('^https://nvd\\.nist\\.gov/vuln/detail/')
  );
});

test('Domain details link', async () => {
  await page.goto('/inventory/vulnerabilities');
  await page.getByRole('row').nth(2).getByRole('link').nth(1).click();
  await expect(page).toHaveURL(new RegExp('/inventory/domain/'));
});

test('Vulnerability details', async () => {
  await page.goto('/inventory/vulnerabilities');
  await page.getByRole('row').nth(2).getByRole('link').nth(2).click();
  await expect(page).toHaveURL(new RegExp('/inventory/vulnerability/'));
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Installed (Known) Products' })
  ).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Provenance' })).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Vulnerability Detection History' })
  ).toBeVisible();
});
