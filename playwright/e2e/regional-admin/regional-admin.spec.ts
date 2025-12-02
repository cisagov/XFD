import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import type { Page, Locator } from '@playwright/test';
import { openMenuIfCollapsed, navScope } from '../../utils/menu_collapse';
import { ROUTES } from '../../../frontend/src/constants/routes';
import { ENDPOINTS } from '../../../frontend/src/constants/endpoints';
import { UUID_RX } from '../../utils/constants';
import {
  openFiltersDrawer,
  closeFilterDrawer,
  ensureSectionOpen,
  selectFromAutocomplete,
  selectAnyOrganization,
  isVisible,
  urlHasBothFilters,
  VS,
  INV
} from '../../utils/filters';

test.describe('Home Page — Regional Admin Permissions', () => {
  test('Admin Hub expands and shows expected items', async ({
    pageAsRegionalAdmin
  }) => {
    const page = pageAsRegionalAdmin;
    await page.goto(ROUTES.HOME);

    await openMenuIfCollapsed(page);
    const nav = await navScope(page);

    const lcButton = nav.getByRole('button', { name: /^admin hub$/i }).first();
    await expect(lcButton, 'Admin Hub toggle should exist').toBeVisible();

    if ((await lcButton.getAttribute('aria-expanded')) !== 'true') {
      await lcButton.click();
      await expect(lcButton).toHaveAttribute('aria-expanded', 'true');
    }

    const expectedItems = [
      /manage organizations/i,
      /manage users/i,
      /user registration/i
    ];

    for (const rx of expectedItems) {
      const item = nav
        .getByRole('menuitem', { name: rx })
        .first()
        .or(nav.getByRole('link', { name: rx }).first());
      await expect(item, `Missing Admin Hub item: ${rx}`).toBeVisible();
    }
  });

  test('should block access to /admin-tools for Regional Admin', async ({
    pageAsRegionalAdmin
  }) => {
    const page = pageAsRegionalAdmin;

    await page.goto(ROUTES.ADMIN_TOOLS, { waitUntil: 'networkidle' });

    const pathname = new URL(page.url()).pathname;
    expect(
      pathname !== ROUTES.ADMIN_TOOLS,
      'Regional Admin should not remain on /admin-tools'
    ).toBeTruthy();

    const forbiddenText = page.getByText(
      /(not authorized|forbidden|access denied|permission denied)/i
    );
    const notFoundText = page.getByText(/(not found|404)/i);

    const hasForbidden = await forbiddenText.count();
    const hasNotFound = await notFoundText.count();
    expect(
      hasForbidden > 0 || hasNotFound > 0 || pathname !== ROUTES.ADMIN_TOOLS,
      'Regional Admin should see a redirect or forbidden message when visiting /admin-tools'
    ).toBeTruthy();
  });
});

test.describe('Findings Library — Regional Admin interactions', () => {
  test('first "View domain details for …" opens /inventory/domain/<uuid>', async ({
    pageAsRegionalAdmin
  }) => {
    const page = pageAsRegionalAdmin;

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

    const uuidRoute = new RegExp(
      `${ROUTES.DOMAIN.replace(':domainId', UUID_RX)}/?$`,
      'i'
    );

    await Promise.all([
      page.waitForURL(uuidRoute, { timeout: 10_000 }),
      firstBtn.click()
    ]);

    await expect(page).toHaveURL(uuidRoute);

    if (identifier) {
      const idRx = new RegExp(
        `\\b${identifier.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`,
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

test.describe('Findings Library — Regional Admin tables', () => {
  test('Domains tab shows "Domains Table"', async ({ pageAsRegionalAdmin }) => {
    const page = pageAsRegionalAdmin;
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
    pageAsRegionalAdmin
  }) => {
    const page = pageAsRegionalAdmin;
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

test.describe('VSDashboard — Regional Admin', () => {
  test('shows "Latest Scanning Summary"', async ({ pageAsRegionalAdmin }) => {
    const page = pageAsRegionalAdmin;
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

test.describe('Admin API Test — Regional Admin', () => {
  test('GET /metrics/customers is blocked (403)', async ({
    pageAsRegionalAdmin
  }) => {
    await pageAsRegionalAdmin.goto(ROUTES.HOME);

    const backend = process.env.BACKEND_DOMAIN;
    const url = `${backend}${ENDPOINTS.METRICS_CUSTOMERS}`;

    const res = await pageAsRegionalAdmin.context().request.get(url, {
      headers: { Accept: 'text/csv' }
    });

    expect([401, 403]).toContain(res.status());
  });
});

test.describe('VSDashboard — Regional Admin: Filter permissions', () => {
  test('Filters are enabled; selecting Region & Organization updates state (URL or empty-state)', async ({
    pageAsRegionalAdmin
  }) => {
    const page = pageAsRegionalAdmin;
    await page.goto(ROUTES.VSDASHBOARD);

    await openFiltersDrawer(page, VS);

    const chosenRegion = await selectFromAutocomplete(
      page,
      /^region$/i,
      /Region\s*2/i
    );
    await page.waitForTimeout(400);
    const chosenOrg = await selectAnyOrganization(page, /^organization$/i);
    await page.waitForTimeout(400);
    await closeFilterDrawer(page, VS, { assertHidden: true });
    const urlHasFilters = await urlHasBothFilters(page, VS, 1500);

    const sawEmpty = await isVisible(
      page.getByText(/no data available for this organization/i),
      1500
    );

    let persisted = false;
    if (!urlHasFilters && !sawEmpty) {
      await openFiltersDrawer(page, VS);
      await expect(
        page.getByRole('combobox', { name: /^region$/i }).first()
      ).toHaveValue(chosenRegion);
      await expect(
        page.getByRole('combobox', { name: /^organization$/i }).first()
      ).toHaveValue(chosenOrg);
      await closeFilterDrawer(page, VS, { assertHidden: true });
      persisted = true;
    }

    expect(urlHasFilters || sawEmpty || persisted).toBeTruthy();
  });
});

test.describe('Inventory — Regional Admin: Filter permissions', () => {
  test('Filters are enabled; selecting Regions (checkbox) and Organization (search combobox) updates state', async ({
    pageAsRegionalAdmin
  }) => {
    const page = pageAsRegionalAdmin;

    await page.goto(ROUTES.INVENTORY);

    await openFiltersDrawer(page, INV);

    await ensureSectionOpen(page, /regions?/i);

    const allRegions = page
      .getByRole('checkbox', { name: /^all regions$/i })
      .first();
    if (await allRegions.isVisible().catch(() => false)) {
      if (await allRegions.isChecked()) {
        await allRegions.click();
        await expect(allRegions).not.toBeChecked();
      }
    }

    const region2 = page
      .getByRole('checkbox', { name: /^region\s*2$/i })
      .first();
    await expect(region2).toBeVisible();
    await region2.click();
    await expect(region2).toBeChecked();

    await ensureSectionOpen(page, /organizations?/i);
    const chosenOrg = await selectAnyOrganization(
      page,
      /search organizations?/i
    );

    await closeFilterDrawer(page, INV, { assertHidden: false });

    const urlHasFilters = await urlHasBothFilters(page, INV, 1500);

    const emptyState = page.locator(
      [
        'text=/no data available/i',
        'text=/no assets/i',
        'text=/no results/i',
        'text=/please select another organization/i'
      ].join(', ')
    );
    const sawEmpty = await isVisible(emptyState, 1500);

    let persisted = false;
    if (!urlHasFilters && !sawEmpty) {
      await openFiltersDrawer(page, INV);

      await ensureSectionOpen(page, /regions?/i);
      await expect(
        page.getByRole('checkbox', { name: /^region\s*2$/i }).first()
      ).toBeChecked();

      await ensureSectionOpen(page, /organizations?/i);

      const baseOrgName = chosenOrg.replace(/\s*\([^)]*\)\s*$/, '').trim();

      const selectedOrgCard = page
        .getByRole('checkbox', { name: new RegExp(baseOrgName, 'i') })
        .first();

      await expect(
        selectedOrgCard,
        'Selected organization card should persist when drawer is reopened'
      ).toBeVisible();
      await expect(selectedOrgCard).toBeChecked();

      await closeFilterDrawer(page, INV, { assertHidden: false });
      persisted = true;
    }

    expect(urlHasFilters || sawEmpty || persisted).toBeTruthy();
  });
});
