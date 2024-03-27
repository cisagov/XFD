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
test('Inventory', async () => {
  await page.getByRole('link', { name: 'Inventory' }).click();
  await expect(page).toHaveURL('/inventory');
  await page.getByRole('button', { name: 'IP(s)' }).click();
  await page.getByRole('button', { name: 'Severity' }).click();
  await page.getByLabel('Sort by:').first().click();
  await page.getByRole('option', { name: 'Domain Name' }).click();
  await page.getByLabel('Sort by:').first().click();
  await page.getByRole('option', { name: 'IP' }).click();
  await page.getByLabel('Sort by:').first().click();
  await page.getByRole('option', { name: 'Last Seen' }).click();
  await page.getByLabel('Sort by:').first().click();
  await page.getByRole('option', { name: 'First Seen' }).click();
  await page.screenshot({
    path: 'test-results/img/global-admin/inventory.png'
  });
});

test('Domains', async () => {
  await page.goto('/inventory');
  await page.getByRole('link', { name: 'All Domains' }).click();
  await expect(page).toHaveURL('/inventory/domains');
  if ((await page.getByLabel('Go to next page').isDisabled()) == false) {
    await page.getByLabel('Go to next page').click();
  }
  if ((await page.getByLabel('Go to previous page').isDisabled()) == false) {
    await page.getByLabel('Go to previous page').click();
  }
  await page.screenshot({ path: 'test-results/img/global-admin/domains.png' });
});

test('Domain details', async () => {
  await page.goto('/inventory/domains');
  await page.getByRole('row').nth(2).getByRole('link').click();
  await expect(page).toHaveURL(new RegExp('/inventory/domain/'));
  await expect(page.getByText('IP:')).toBeVisible();
  await expect(page.getByText('First Seen:')).toBeVisible();
  await expect(page.getByText('Last Seen:')).toBeVisible();
  await expect(page.getByText('Organization:')).toBeVisible();
  await page.screenshot({
    path: 'test-results/img/global-admin/domain_details.png'
  });
});

test('Domains filter', async () => {
  await page.goto('/inventory/domains');
  await page.locator('#organizationName').click();
  await page.locator('#organizationName').fill('Homeland');
  await page.locator('#organizationName').press('Enter');
  let rowCount = await page.getByRole('row').count();
  for (let it = 2; it < rowCount; it++) {
    await expect(
      page.getByRole('row').nth(it).getByRole('cell').nth(1)
    ).toContainText('Homeland');
  }
  await page.screenshot({
    path: 'test-results/img/global-admin/domain_filter.png'
  });
});
