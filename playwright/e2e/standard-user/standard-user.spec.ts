import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import type { Page, Locator } from '@playwright/test';
import { openMenuIfCollapsed, navScope } from '../../utils/menu_collapse';
import { ROUTES } from '../../../frontend/src/constants/routes';
import { ENDPOINTS } from '../../../frontend/src/constants/endpoints';
import { UUID_RX } from '../../utils/constants';

const IS_CI =
  (process.env.CI ?? '').toLowerCase() === 'true' || process.env.CI === '1';

test.describe('Home Page — Standard User Permissions', () => {
  test('should not display "Admin Hub" button, link, or text', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto(ROUTES.HOME);

    await openMenuIfCollapsed(page);
    const nav = await navScope(page);

    const adminHubText = page.getByText(/admin hub/i);
    await expect(
      adminHubText,
      '"Admin Hub" text should not be visible to Standard User'
    ).toHaveCount(0);

    const adminHubButton = page.getByRole('button', { name: /admin hub/i });
    await expect(
      adminHubButton,
      'No "Admin Hub" button should be present'
    ).toHaveCount(0);

    const adminHubLink = page.getByRole('link', { name: /admin hub/i });
    await expect(
      adminHubLink,
      'No "Admin Hub" link should be visible'
    ).toHaveCount(0);
  });

  test('should block access to /admin-tools for Standard User', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;

    await page.goto(ROUTES.ADMIN_TOOLS, { waitUntil: 'networkidle' });

    const pathname = new URL(page.url()).pathname;
    expect(
      pathname !== ROUTES.ADMIN_TOOLS,
      'Standard User should not remain on /admin-tools'
    ).toBeTruthy();

    const forbiddenText = page.getByText(
      /(not authorized|forbidden|access denied|permission denied)/i
    );
    const notFoundText = page.getByText(/(not found|404)/i);

    const hasForbidden = await forbiddenText.count();
    const hasNotFound = await notFoundText.count();
    expect(
      hasForbidden > 0 || hasNotFound > 0 || pathname !== ROUTES.ADMIN_TOOLS,
      'Standard User should see a redirect or forbidden message when visiting /admin-tools'
    ).toBeTruthy();
  });
});

test.describe('VSDashboard — Standard User: Filter permissions', () => {
  test.fixme(IS_CI, 'TODO: CI environment missing required data');
  test('Filter button opens drawer; Region & Organization are disabled and not expandable', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto(ROUTES.VSDASHBOARD);

    const filterBtn = page.getByRole('button', { name: /^filter$/i });
    await expect(filterBtn).toBeVisible();
    await expect(filterBtn).toBeEnabled();

    await filterBtn.click();
    const drawerHeading = page.getByRole('heading', { name: /^filter$/i });
    await expect(drawerHeading).toBeVisible();

    await expectComboboxDisabledAndClosed(page, /^region$/i);
    await expectComboboxDisabledAndClosed(page, /^organization$/i);
  });
});

/* ---------------- helpers ---------------- */

async function expectComboboxDisabledAndClosed(page: Page, label: RegExp) {
  const combo = page.getByRole('combobox', { name: label }).first();
  await expect(combo, `Missing combobox: ${label}`).toBeVisible();

  const ariaDisabled = await combo.getAttribute('aria-disabled');
  const nativelyDisabled = await combo.isDisabled().catch(() => false);
  expect(
    nativelyDisabled || ariaDisabled === 'true',
    `Expected ${comboName(label)} to be disabled`
  ).toBeTruthy();

  await expect(combo).not.toHaveAttribute('aria-expanded', 'true');

  await combo.click({ force: true });
  await expect(combo).not.toHaveAttribute('aria-expanded', 'true');

  await expect(page.getByRole('listbox')).toHaveCount(0, { timeout: 300 });
}

function comboName(rx: RegExp) {
  return `combobox "${rx.source}"`;
}

test.describe('Findings Library — Standard User interactions', () => {
  test.fixme(IS_CI, 'TODO: CI environment missing required data');
  test('first "View domain details for …" opens /inventory/domain/<uuid>', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;

    await page.goto(ROUTES.INVENTORY);
    await expect(
      page.getByRole('heading', { name: /findings library/i })
    ).toBeVisible();

    const detailsButtons = page
      .getByRole('button', { name: /view domain details for/i })
      .or(page.getByRole('link', { name: /view domain details for/i }));

    await expect(
      detailsButtons.first(),
      'Expected at least one "View domain details for …" control'
    ).toBeVisible();

    const firstBtn = detailsButtons.first();
    const a11yName =
      (await firstBtn.getAttribute('aria-label')) ??
      (await firstBtn.textContent()) ??
      '';
    const match = a11yName.match(/view domain details for\s+(.+)$/i);
    const identifier = (match?.[1] ?? '').trim();

    // Build a URL regex directly from the route constant by replacing :domainId with a UUID pattern
    const domainUuidRx = new RegExp(
      `${ROUTES.DOMAIN.replace(':domainId', UUID_RX)}/?$`,
      'i'
    );

    await Promise.all([
      page.waitForURL(domainUuidRx, { timeout: 10_000 }),
      firstBtn.click()
    ]);

    await expect(page).toHaveURL(domainUuidRx);

    if (identifier) {
      const idRx = new RegExp(
        `\\b${identifier.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\$&')}\\b`,
        'i'
      );
      const headingWithId = page.getByRole('heading', { name: idRx });
      if (await headingWithId.count()) {
        await expect(headingWithId.first()).toBeVisible();
      } else {
        await expect(page.getByText(idRx)).toBeVisible();
      }
    }
  });
});

test.describe('Findings Library — Standard User tables', () => {
  test('Domains tab shows "Domains Table"', async ({ pageAsStandardUser }) => {
    const page = pageAsStandardUser;
    await page.goto(ROUTES.INVENTORY);

    await expect(
      page.getByRole('heading', { name: /findings library/i })
    ).toBeVisible();
    const tabs = page
      .getByRole('tablist', { name: /findings section tabs/i })
      .first();
    await expect(tabs).toBeVisible();

    const domainsTab = tabs.getByRole('tab', { name: /^domains$/i });
    await domainsTab.click();
    await expect(domainsTab).toHaveAttribute('aria-selected', 'true');

    const domainsTable = await getNamedTable(page, /domains table/i);
    await expect(
      domainsTable,
      'Expected "Domains Table" to be visible'
    ).toBeVisible();
  });

  test('Vulnerabilities tab shows "Vulnerabilities Table"', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto(ROUTES.INVENTORY);

    await expect(
      page.getByRole('heading', { name: /findings library/i })
    ).toBeVisible();
    const tabs = page
      .getByRole('tablist', { name: /findings section tabs/i })
      .first();
    await expect(tabs).toBeVisible();

    const vulnsTab = tabs.getByRole('tab', { name: /^vulnerabilities$/i });
    await vulnsTab.click();
    await expect(vulnsTab).toHaveAttribute('aria-selected', 'true');

    const vulnsTable = await getNamedTable(page, /vulnerabilities table/i);
    await expect(
      vulnsTable,
      'Expected "Vulnerabilities Table" to be visible'
    ).toBeVisible();
  });
});

/* ---------------- helpers ---------------- */

async function getNamedTable(page: Page, nameRx: RegExp): Promise<Locator> {
  const table = page.getByRole('table', { name: nameRx });
  if (await table.count()) return table.first();

  const grid = page.getByRole('grid', { name: nameRx });
  if (await grid.count()) return grid.first();

  const generic = page.getByRole('generic', { name: nameRx });
  if (await generic.count()) return generic.first();

  const labelled = page.getByLabel(nameRx).first();
  return labelled;
}

test.describe('VSDashboard — Standard User', () => {
  test.fixme(IS_CI, 'TODO: CI environment missing required data');
  test('shows "Latest Scanning Summary"', async ({ pageAsStandardUser }) => {
    const page = pageAsStandardUser;
    await page.goto(ROUTES.VSDASHBOARD);

    const summary = page
      .getByRole('heading', { name: /latest scanning summary/i })
      .or(page.getByText(/latest scanning summary/i));

    await expect(
      summary,
      'Expected "Latest Scanning Summary" on VSDashboard'
    ).toBeVisible();
  });
});

test.describe('Admin API Test — Standard User', () => {
  test('GET /metrics/customers is blocked (403)', async ({
    pageAsStandardUser
  }) => {
    await pageAsStandardUser.goto(ROUTES.HOME);

    const backend = process.env.BACKEND_DOMAIN;
    const url = `${backend}${ENDPOINTS.METRICS_CUSTOMERS}`;

    const res = await pageAsStandardUser.context().request.get(url, {
      headers: { Accept: 'text/csv' }
    });

    expect([401, 403]).toContain(res.status());
  });
});
