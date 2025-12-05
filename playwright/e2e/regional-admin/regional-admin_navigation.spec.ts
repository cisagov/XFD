import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import { ROUTES } from '../../../frontend/src/constants/routes';
import {
  navFromHome,
  openAdminHub,
  openLearningCenter,
  openSupport,
  clickTopLevelNavAndAssert,
  assertSupportMailto,
  assertLearningCenterExternalLink,
  assertLogoutShowsSignIn
} from '../../utils/navigation_bar';

test.describe('Home Page — Regional Admin Permissions and Navigation', () => {
  test('Admin Hub expands and shows expected items', async ({
    pageAsRegionalAdmin
  }) => {
    const nav = await navFromHome(pageAsRegionalAdmin);
    await openAdminHub(nav);

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

  test('Admin Hub → Manage Organizations navigates to /organizations', async ({
    pageAsRegionalAdmin
  }) => {
    const page = pageAsRegionalAdmin;
    const nav = await navFromHome(page);
    await openAdminHub(nav);

    const manageOrgsItem = nav
      .getByRole('menuitem', { name: /manage organizations/i })
      .first()
      .or(nav.getByRole('link', { name: /manage organizations/i }).first());

    await expect(manageOrgsItem).toBeVisible();

    await Promise.all([
      page.waitForURL(new RegExp(`${ROUTES.ORGANIZATIONS}/?$`, 'i')),
      manageOrgsItem.click()
    ]);

    await expect(page).toHaveURL(new RegExp(`${ROUTES.ORGANIZATIONS}/?$`, 'i'));
    await expect(
      page.getByRole('heading', { name: /organizations/i })
    ).toBeVisible();
  });

  test('Admin Hub → Manage Users navigates to /users', async ({
    pageAsRegionalAdmin
  }) => {
    const page = pageAsRegionalAdmin;
    const nav = await navFromHome(page);
    await openAdminHub(nav);

    const manageUsersItem = nav
      .getByRole('menuitem', { name: /manage users/i })
      .first()
      .or(nav.getByRole('link', { name: /manage users/i }).first());

    await expect(manageUsersItem).toBeVisible();

    await Promise.all([
      page.waitForURL(new RegExp(`${ROUTES.USERS}/?$`, 'i')),
      manageUsersItem.click()
    ]);

    await expect(page).toHaveURL(new RegExp(`${ROUTES.USERS}/?$`, 'i'));
    await expect(page.getByRole('heading', { name: /users/i })).toBeVisible();
  });

  test('Admin Hub → User Registration navigates to /global-admin-dashboard', async ({
    pageAsRegionalAdmin
  }) => {
    const page = pageAsRegionalAdmin;
    const nav = await navFromHome(page);
    await openAdminHub(nav);

    const userRegItem = nav
      .getByRole('menuitem', { name: /user registration/i })
      .first()
      .or(nav.getByRole('link', { name: /user registration/i }).first());

    await expect(userRegItem).toBeVisible();

    await Promise.all([
      page.waitForURL(new RegExp(`${ROUTES.REGION_ADMIN_DASHBOARD}/?$`, 'i')),
      userRegItem.click()
    ]);

    await expect(page).toHaveURL(
      new RegExp(`${ROUTES.REGION_ADMIN_DASHBOARD}/?$`, 'i')
    );

    await expect(
      page.getByRole('heading', {
        name: /Regional Admin dashboard|user registration/i
      })
    ).toBeVisible();
  });
});

test.describe('Home — Regional Admin Navigation (responsive)', () => {
  test('Vulnerability Scanning navigates to /VSDashboard', async ({
    pageAsRegionalAdmin
  }) => {
    await clickTopLevelNavAndAssert(
      pageAsRegionalAdmin,
      /vulnerability scanning/i,
      new RegExp(`${ROUTES.VSDASHBOARD}/?$`, 'i'),
      /vulnerability scanning/i
    );
  });

  test('Findings Library navigates to /inventory', async ({
    pageAsRegionalAdmin
  }) => {
    await clickTopLevelNavAndAssert(
      pageAsRegionalAdmin,
      /findings library/i,
      new RegExp(`${ROUTES.INVENTORY}/?$`, 'i'),
      /findings library|inventory/i
    );
  });
});

test.describe('Home — Regional Admin: Learning Center nav', () => {
  test('Learning Center expands and shows expected items', async ({
    pageAsRegionalAdmin
  }) => {
    const nav = await navFromHome(pageAsRegionalAdmin);
    await openLearningCenter(nav);

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
    pageAsRegionalAdmin
  }) => {
    const nav = await navFromHome(pageAsRegionalAdmin);
    await openLearningCenter(nav);

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

  test('Learning Center → CISA Resources links to cisa.gov', async ({
    pageAsRegionalAdmin
  }) => {
    const CISA_RX = /^https:\/\/(www\.)?cisa\.gov(\/.*)?$/;

    await assertLearningCenterExternalLink(
      pageAsRegionalAdmin,
      /cisa resources/i,
      CISA_RX
    );
  });
});

test.describe('Home — Regional Admin: Support nav', () => {
  test('Support expands and shows expected items', async ({
    pageAsRegionalAdmin
  }) => {
    const nav = await navFromHome(pageAsRegionalAdmin);
    await openSupport(nav);

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
    pageAsRegionalAdmin
  }) => {
    const nav = await navFromHome(pageAsRegionalAdmin);

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

  test('Support → General Questions is a mailto link', async ({
    pageAsRegionalAdmin
  }) => {
    await assertSupportMailto(pageAsRegionalAdmin, /general questions/i);
  });

  test('Support → Report Bug is a mailto link', async ({
    pageAsRegionalAdmin
  }) => {
    await assertSupportMailto(pageAsRegionalAdmin, /report bug/i);
  });

  test('Support → Send Feedback is a mailto link', async ({
    pageAsRegionalAdmin
  }) => {
    await assertSupportMailto(pageAsRegionalAdmin, /send feedback/i);
  });
});

test.describe('Home — Regional Admin: My Account Navigation', () => {
  test('Account Settings navigates to Account Settings', async ({
    pageAsRegionalAdmin
  }) => {
    const nav = await navFromHome(pageAsRegionalAdmin);

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
      pageAsRegionalAdmin.waitForURL(new RegExp(`${ROUTES.SETTINGS}/?$`, 'i'), {
        timeout: 10_000
      }),
      accountSettings.click()
    ]);

    await expect(pageAsRegionalAdmin).toHaveURL(
      new RegExp(`${ROUTES.SETTINGS}/?$`, 'i')
    );
    await expect(
      pageAsRegionalAdmin.getByRole('heading', { name: /my account/i })
    ).toBeVisible();
  });

  test('Logout logs the user out and shows the sign-in page', async ({
    pageAsRegionalAdmin
  }) => {
    await assertLogoutShowsSignIn(pageAsRegionalAdmin);
  });
});

// TODO Currently only working part of Learning Center is CISA Resources, will need to add tests once rest of Learning Center is finished
// Learnging Center:
//
//  Sector Vulnerability Snapshots:
//   - Communications
//   - Financial Services
//   - Food and Agriculture
//   - Healthcare and Public Health
//   - Information Technology
//   - Transportation Systems
//   - Water and Wastewater Systems
//  User Guide
//  VS FAQ
//  VS Glossary
//  VS Methodology
