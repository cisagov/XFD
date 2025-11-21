import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import { ROUTES } from '../../../frontend/src/constants/routes';
import { runAxeAndFailOnSerious } from '../../utils/a11y';
import { UUID_RX } from '../../utils/constants';
import {
  openFiltersDrawer,
  closeFilterDrawer,
  VS,
  INV
} from '../../utils/filters';
import { assertLogoutShowsSignIn } from '../../utils/navigation_bar';

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

  test('Organizations: no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.ORGANIZATIONS);

    await expect(
      page.getByRole('heading', { name: /organizations/i })
    ).toBeVisible();

    await runAxeAndFailOnSerious(page, makeAxeBuilder, ti, 'Organizations');
  });

  // Users (Admin Hub → Manage Users)
  test('Users: no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.USERS);

    await expect(page.getByRole('heading', { name: /users/i })).toBeVisible();

    await runAxeAndFailOnSerious(page, makeAxeBuilder, ti, 'Users');
  });

  // Global Admin Dashboard / User Registration
  test('Global Admin Dashboard (User Registration): no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;
    await page.goto(ROUTES.GLOBAL_ADMIN_DASHBOARD);

    // Pick a heading that actually exists here — adjust if your page title differs
    const heading = page
      .getByRole('heading', { name: /global admin dashboard/i })
      .or(page.getByRole('heading', { name: /user registration/i }));

    await expect(heading.first()).toBeVisible();

    await runAxeAndFailOnSerious(
      page,
      makeAxeBuilder,
      ti,
      'Global Admin Dashboard / User Registration'
    );
  });

  test('Landing / Sign-in page: no serious/critical violations', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsGlobalAdmin;

    await assertLogoutShowsSignIn(pageAsGlobalAdmin);

    await runAxeAndFailOnSerious(
      page,
      makeAxeBuilder,
      ti,
      'Landing / Sign-in page'
    );
  });
});
