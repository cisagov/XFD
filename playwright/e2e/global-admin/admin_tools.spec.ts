import { test, expect, Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });
let page: Page;

test.beforeAll(async ({ browser }) => {
  page = await browser.newPage();
  await page.goto('/');
});

test.afterAll(async () => {
  await page.close();
});
test('admin tools', async () => {
  // Expect Admin Tools to show form.
  await page.goto('/');
  await page.getByRole('link', { name: 'My Account' }).click();
  await page.getByRole('menuitem', { name: 'Admin Tools' }).click();
  await expect(page.getByRole('link', { name: 'Scan History' })).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Manually run scheduler' })
  ).toBeVisible();
  await page.locator('#name').selectOption('shodan');
  await expect(page.locator('#name')).toHaveValue('shodan');
  await page.getByText('Limit enabled organizations').click();
  await page.getByText("Allow any organization's").click();
  await page.getByText('Run scan once').click();
  await page.getByText('Run scan once').click();
  await page.getByTestId('textInput').click();
  await page.getByTestId('textInput').fill('05');
  await page.locator('#frequencyUnit').selectOption('hour');
  await expect(page.getByTestId('form').getByTestId('button')).toBeVisible();
  await expect(page.getByLabel('File must be in a CSV format')).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Export as CSV' })
  ).toBeVisible();
});

test('Scan Table', async () => {
  await page.goto('/');
  await page.getByRole('link', { name: 'My Account' }).click();
  await page.getByRole('menuitem', { name: 'Admin Tools' }).click();
  await expect(
    page
      .getByRole('row', { name: 'censys Passive Single Scan 2' })
      .getByRole('img')
      .first()
  ).toBeVisible();
  await expect(
    page
      .getByRole('row', { name: 'censys Passive Single Scan 2' })
      .locator('span')
      .getByRole('img')
  ).toBeVisible();
  await expect(page.locator('tbody')).toContainText('censys');
});

test('Scan History', async () => {
  await page.goto('/');
  await page.getByRole('link', { name: 'My Account' }).click();
  await page.getByRole('menuitem', { name: 'Admin Tools' }).click();
  await page.getByRole('link', { name: 'Scan History' }).click();
  await page
    .getByRole('row')
    .nth(2)
    .locator('td')
    .nth(5)
    .locator('path')
    .click();
  await expect(page.locator('tbody')).toContainText(
    'Logs (View all on CloudWatch)'
  );
  await expect(page.getByRole('heading', { name: 'Input' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Output' })).toBeVisible();
});
