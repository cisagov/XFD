import { test, expect, Page } from '@playwright/test';
import exp from 'constants';

test.describe.configure({ mode: 'serial' });
let page: Page;

test.beforeAll(async ({ browser }) => {
  page = await browser.newPage();
  await page.goto('/');
});

test.afterAll(async () => {
  await page.close();
});
test('home', async () => {
  // Expect home page to show Latest Vulnerabilities.
  await expect(
    page.getByRole('heading', { name: 'Latest Vulnerabilities' })
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Open Vulnerabilities by Domain' })
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Most Common Ports' })
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Most Common Vulnerabilities' })
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Severity Levels' })
  ).toBeVisible();
  await expect(
    page.getByPlaceholder('Search a domain, vuln, port, service, IP')
  ).toBeVisible();
  await expect(page.getByRole('link', { name: 'Inventory' })).toBeVisible();
  await page.screenshot({ path: 'test-results/img/global-admin/home.png' });
});

test('Open Vulnerabilities by Domain', async () => {
  await page.getByRole('button', { name: 'All' }).click();
  await page.screenshot({
    path: 'test-results/img/global-admin/open_vuln_all.png'
  });
  if (
    (await page.getByRole('button', { name: 'Medium' }).isDisabled()) == false
  ) {
    await page.getByRole('button', { name: 'Medium' }).click();
    await page.screenshot({
      path: 'test-results/img/global-admin/open_vuln_medium.png'
    });
  }
  if (
    (await page.getByRole('button', { name: 'High' }).isDisabled()) == false
  ) {
    await page.getByRole('button', { name: 'High' }).click();
    await page.screenshot({
      path: 'test-results/img/global-admin/open_vuln_high.png'
    });
  }
  if ((await page.getByLabel('Go to next page').isDisabled()) == false) {
    await page.getByLabel('Go to next page').click();
  }
  if ((await page.getByLabel('Go to previous page').isDisabled()) == false) {
    await page.getByLabel('Go to previous page').click();
  }
});
