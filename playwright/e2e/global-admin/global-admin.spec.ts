import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import type { Page, Locator } from '@playwright/test';
import { openMenuIfCollapsed, navScope } from '../../utils/menu_collapse';
import { ROUTES } from '../../../frontend/src/constants/routes';
import { ENDPOINTS } from '../../../frontend/src/constants/endpoints';
import { runAxeAndFailOnSerious } from '../../utils/a11y';
import {
  openFiltersDrawer,
  closeFilterDrawer,
  ensureSectionOpen,
  selectFromAutocomplete,
  selectAnyOrganization,
  isVisible,
  hasValue,
  urlHasBothFilters,
  escapeForTextSelector,
  VS,
  INV
} from '../../utils/filters';

const UUID_RX = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';

test.describe('Home Page — Global Admin Permissions', () => {
  test('Admin Hub expands and shows expected items', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
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
      /admin tools/i,
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

  test('should have access to /admin-tools for Global Admin', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    const response = await page.goto(ROUTES.ADMIN_TOOLS, {
      waitUntil: 'domcontentloaded'
    });

    await expect(page).toHaveURL(ROUTES.ADMIN_TOOLS);

    expect(
      response && response.ok(),
      `Expected 2xx response; got ${response?.status()}`
    ).toBeTruthy();

    await expect(page.getByRole('tab', { name: /^scans$/i })).toHaveAttribute(
      'aria-selected',
      'true'
    );

    await expect(
      page.getByRole('button', { name: /manually run scheduler/i })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: /add a scan/i })
    ).toBeVisible();
  });
});

test.describe('Home — Global Admin Navigation (responsive)', () => {
  async function getNavItem(page: Page, nameRx: RegExp) {
    const navDialog = page.getByRole('dialog', { name: /navigation menu/i });
    if (await navDialog.isVisible()) {
      return navDialog.getByRole('menuitem', { name: nameRx });
    }

    const mainNav = page.getByRole('navigation', { name: /main navigation/i });
    const link = mainNav.getByRole('link', { name: nameRx });
    if (await link.count()) return link;
    const btn = mainNav.getByRole('button', { name: nameRx });
    if (await btn.count()) return btn;

    return page.getByText(nameRx, { exact: false });
  }

  async function openMobileMenuIfPresent(page: Page) {
    const trigger = page
      .getByRole('button', { name: /menu|open.*menu|navigation/i })
      .first();
    if (await trigger.isVisible()) {
      await trigger.click();
      await expect(
        page.getByRole('dialog', { name: /navigation menu/i })
      ).toBeVisible();
    }
  }

  test('Vulnerability Scanning navigates to /VSDashboard', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.HOME);

    await openMobileMenuIfPresent(page);
    const item = await getNavItem(page, /vulnerability scanning/i);
    await expect(
      item,
      'Nav item "Vulnerability Scanning" should be visible'
    ).toBeVisible();

    await Promise.all([
      page.waitForURL(new RegExp(`${ROUTES.VSDASHBOARD}/?$`, 'i')),
      item.click()
    ]);

    await expect(page).toHaveURL(new RegExp(`${ROUTES.VSDASHBOARD}/?$`, 'i'));
    await expect(
      page.getByRole('heading', { name: /vulnerability scanning/i })
    ).toBeVisible();
  });

  test('Findings Library navigates to /inventory', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.HOME);

    await openMobileMenuIfPresent(page);
    const item = await getNavItem(page, /findings library/i);
    await expect(
      item,
      'Nav item "Findings Library" should be visible'
    ).toBeVisible();

    await Promise.all([
      page.waitForURL(new RegExp(`${ROUTES.INVENTORY}/?$`, 'i')),
      item.click()
    ]);

    await expect(page).toHaveURL(new RegExp(`${ROUTES.INVENTORY}/?$`, 'i'));
    await expect(
      page.getByRole('heading', { name: /findings library|inventory/i })
    ).toBeVisible();
  });
});

test.describe('Home — Global Admin: Learning Center nav', () => {
  test('Learning Center expands and shows expected items', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.HOME);

    await openMenuIfCollapsed(page);
    const nav = await navScope(page);

    const lcButton = nav
      .getByRole('button', { name: /^learning center$/i })
      .first();
    await expect(lcButton, 'Learning Center toggle should exist').toBeVisible();

    if ((await lcButton.getAttribute('aria-expanded')) !== 'true') {
      await lcButton.click();
      await expect(lcButton).toHaveAttribute('aria-expanded', 'true');
    }

    const expectedItems = [
      /cisa resources/i,
      /sector vulnerability snapshots/i,
      /user guide/i,
      /vs faq/i,
      /vs glossary/i,
      /vs methodology/i
    ];

    for (const rx of expectedItems) {
      const item = nav
        .getByRole('menuitem', { name: rx })
        .first()
        .or(nav.getByRole('link', { name: rx }).first());
      await expect(item, `Missing Learning Center item: ${rx}`).toBeVisible();
    }
  });

  test('Sector Vulnerability Snapshots shows sector list', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.HOME);

    await openMenuIfCollapsed(page);
    const nav = await navScope(page);

    const lcButton = nav
      .getByRole('button', { name: /^learning center$/i })
      .first();
    if (
      (await lcButton.isVisible()) &&
      (await lcButton.getAttribute('aria-expanded')) !== 'true'
    ) {
      await lcButton.click();
      await expect(lcButton).toHaveAttribute('aria-expanded', 'true');
    }

    const snapshots = nav
      .getByRole('menuitem', { name: /sector vulnerability snapshots/i })
      .first()
      .or(
        nav
          .getByRole('link', { name: /sector vulnerability snapshots/i })
          .first()
      );
    await expect(snapshots).toBeVisible();
    await snapshots.click();

    const sectors = [
      /communications/i,
      /financial services/i,
      /food and agriculture/i,
      /healthcare and public health/i,
      /information technology/i,
      /transportation systems/i,
      /water and wastewater systems/i
    ];

    for (const rx of sectors) {
      const sectorItem = nav
        .getByRole('menuitem', { name: rx })
        .first()
        .or(nav.getByRole('link', { name: rx }).first());
      await expect(sectorItem, `Missing sector item: ${rx}`).toBeVisible();
    }
  });
});

test.describe('Home — Global Admin: Support nav', () => {
  test('Support expands and shows expected items', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.HOME);

    await openMenuIfCollapsed(page);
    const nav = await navScope(page);

    const supportToggle = nav
      .getByRole('button', { name: /^support$/i })
      .first();
    await expect(supportToggle, 'Support toggle should exist').toBeVisible();

    if ((await supportToggle.getAttribute('aria-expanded')) !== 'true') {
      await supportToggle.click();
      await expect(supportToggle).toHaveAttribute('aria-expanded', 'true');
    }

    const expectedSupportItems = [
      /general questions/i,
      /report bug/i,
      /send feedback/i
    ];

    for (const rx of expectedSupportItems) {
      const item = nav
        .getByRole('menuitem', { name: rx })
        .first()
        .or(nav.getByRole('link', { name: rx }).first());
      await expect(item, `Missing Support item: ${rx}`).toBeVisible();
    }
  });

  test('Support toggle reflects expanded/collapsed state (aria-expanded)', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.HOME);

    await openMenuIfCollapsed(page);
    const nav = await navScope(page);

    const supportToggle = nav
      .getByRole('button', { name: /^support$/i })
      .first();
    await expect(supportToggle).toBeVisible();

    if ((await supportToggle.getAttribute('aria-expanded')) === 'true') {
      await supportToggle.click();
      await expect(supportToggle).toHaveAttribute('aria-expanded', 'false');
    }

    await supportToggle.click();
    await expect(supportToggle).toHaveAttribute('aria-expanded', 'true');

    await expect(
      nav
        .getByRole('menuitem', { name: /general questions/i })
        .first()
        .or(nav.getByRole('link', { name: /general questions/i }).first())
    ).toBeVisible();

    await supportToggle.click();
    await expect(supportToggle).toHaveAttribute('aria-expanded', 'false');
  });
});

test.describe('Home — Global Admin: Account Settings nav', () => {
  test('Account Settings navigates to /settings', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.HOME);

    await openMenuIfCollapsed(page);
    const nav = await navScope(page);

    const accountSettings = nav
      .getByRole('menuitem', { name: /account settings/i })
      .first()
      .or(nav.getByRole('link', { name: /account settings/i }).first())
      .or(nav.getByRole('button', { name: /account settings/i }).first());

    await expect(
      accountSettings,
      '"Account Settings" should be visible in navigation'
    ).toBeVisible();

    await Promise.all([
      page.waitForURL(new RegExp(`${ROUTES.SETTINGS}/?$`, 'i'), {
        timeout: 10_000
      }),
      accountSettings.click()
    ]);

    await expect(page).toHaveURL(new RegExp(`${ROUTES.SETTINGS}/?$`, 'i'));
    await expect(
      page.getByRole('heading', { name: /my account/i })
    ).toBeVisible();
  });
});

test.describe('Findings Library — Global Admin interactions', () => {
  test('first "View domain details for …" opens /inventory/domain/<uuid>', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;

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

test.describe('Findings Library — Global Admin tables', () => {
  test('Domains tab shows "Domains Table"', async ({ pageAsGlobalAdmin }) => {
    const page = pageAsGlobalAdmin;
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
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
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

test.describe('VSDashboard — Global Admin', () => {
  test('shows "Latest Scanning Summary"', async ({ pageAsGlobalAdmin }) => {
    const page = pageAsGlobalAdmin;
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

test.describe('Admin API Test — Global Admin', () => {
  test('GET /metrics/customers is accessible', async ({
    pageAsGlobalAdmin
  }) => {
    await pageAsGlobalAdmin.goto(ROUTES.HOME);

    const backend = process.env.BACKEND_DOMAIN;
    const url = `${backend}${ENDPOINTS.METRICS_CUSTOMERS}`;

    const res = await pageAsGlobalAdmin.context().request.get(url, {
      headers: { Accept: 'text/csv' }
    });

    expect([200]).toContain(res.status());
  });
});

test.describe('VSDashboard — Global Admin: Filter permissions', () => {
  test('Filters are enabled; selecting Region & Organization updates state (URL or empty-state)', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
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

test.describe('Inventory — Global Admin: Filter permissions', () => {
  test('Filters are enabled; selecting Regions (checkbox) and Organization (search combobox) updates state', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;

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
      const orgInput = page
        .getByRole('combobox', { name: /search organizations?/i })
        .first();

      const chip = page.locator(`text=${escapeForTextSelector(chosenOrg)}`);

      const valueMatches = await hasValue(orgInput, chosenOrg);
      const chipVisible = await isVisible(chip, 500);

      expect(valueMatches || chipVisible).toBeTruthy();

      await closeFilterDrawer(page, INV, { assertHidden: false });
      persisted = true;
    }

    expect(urlHasFilters || sawEmpty || persisted).toBeTruthy();
  });
});

test.describe('A11y — Global Admin (axe, minimal critical surfaces)', () => {
  // Home (static)
  test('Home: no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    await pageAsGlobalAdmin.goto(ROUTES.HOME);
    await runAxeAndFailOnSerious(pageAsGlobalAdmin, makeAxeBuilder, ti, 'Home');
  });

  // VS Dashboard (drawer OPEN)
  test('VSDashboard (drawer open): no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.VSDASHBOARD);
    await openFiltersDrawer(page, VS);
    await runAxeAndFailOnSerious(
      page,
      makeAxeBuilder,
      ti,
      'VSDashboard — drawer open'
    );
    await closeFilterDrawer(page, VS, { assertHidden: true });
  });

  // Inventory — Filters drawer open
  test('Inventory (drawer open): no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.INVENTORY);
    await openFiltersDrawer(page, INV);
    await runAxeAndFailOnSerious(
      page,
      makeAxeBuilder,
      ti,
      'Inventory — drawer open'
    );
    // Inventory drawer may remain mounted; don't require hidden
    await closeFilterDrawer(page, INV, { assertHidden: false });
  });

  // Inventory — Tabs toggled
  test('Inventory — Domains tab: no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.INVENTORY);
    const tabs = page
      .getByRole('tablist', { name: /findings section tabs/i })
      .first();
    const domainsTab = tabs.getByRole('tab', { name: /^domains$/i }).first();
    await domainsTab.click();
    await expect(domainsTab).toHaveAttribute('aria-selected', 'true');
    await runAxeAndFailOnSerious(
      page,
      makeAxeBuilder,
      ti,
      'Inventory — Domains tab'
    );
  });

  test('Inventory — Vulnerabilities tab: no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.INVENTORY);
    const tabs = page
      .getByRole('tablist', { name: /findings section tabs/i })
      .first();
    const vulnsTab = tabs
      .getByRole('tab', { name: /^vulnerabilities$/i })
      .first();
    await vulnsTab.click();
    await expect(vulnsTab).toHaveAttribute('aria-selected', 'true');
    await runAxeAndFailOnSerious(
      page,
      makeAxeBuilder,
      ti,
      'Inventory — Vulnerabilities tab'
    );
  });

  // Domain details (conditional)
  test('Domain details: no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.INVENTORY);

    const details = page
      .getByRole('button', { name: /view domain details for/i })
      .or(page.getByRole('link', { name: /view domain details for/i }));

    const count = await details.count();
    test.skip(count === 0, 'No domain details available to open');

    const domainUuidRx = new RegExp(
      `${ROUTES.DOMAIN.replace(':domainId', UUID_RX)}/?$`,
      'i'
    );

    await Promise.all([
      page.waitForURL(domainUuidRx, { timeout: 10_000 }),
      details.first().click()
    ]);

    await runAxeAndFailOnSerious(page, makeAxeBuilder, ti, 'Domain Details');
  });

  // Settings → My Account (static)
  test('Settings (My Account): no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    await pageAsGlobalAdmin.goto(ROUTES.SETTINGS);
    await runAxeAndFailOnSerious(
      pageAsGlobalAdmin,
      makeAxeBuilder,
      ti,
      'Settings / My Account'
    );
  });

  // Admin Hub → Admin Tools (static)
  test('Admin Tools: no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;

    await page.goto(ROUTES.ADMIN_TOOLS);

    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('main')).toBeVisible({ timeout: 10_000 });

    await runAxeAndFailOnSerious(page, makeAxeBuilder, ti, 'Admin Tools');
  });
});
