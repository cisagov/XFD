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

test.describe('Home Page — Global Admin Permissions and Navigation', () => {
  test('Admin Hub expands and shows expected items', async ({
    pageAsGlobalAdmin
  }) => {
    const nav = await navFromHome(pageAsGlobalAdmin);
    await openAdminHub(nav);

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

  test('Admin Hub → Admin Tools navigates to /admin-tools', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    const nav = await navFromHome(page);
    await openAdminHub(nav);

    const adminToolsItem = nav
      .getByRole('menuitem', { name: /admin tools/i })
      .first()
      .or(nav.getByRole('link', { name: /admin tools/i }).first());

    await expect(adminToolsItem).toBeVisible();

    await Promise.all([
      page.waitForURL(new RegExp(`${ROUTES.ADMIN_TOOLS}/?$`, 'i')),
      adminToolsItem.click()
    ]);

    await expect(page).toHaveURL(new RegExp(`${ROUTES.ADMIN_TOOLS}/?$`, 'i'));

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

  test('Admin Hub → Manage Organizations navigates to /organizations', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
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
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
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
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;
    const nav = await navFromHome(page);
    await openAdminHub(nav);

    const userRegItem = nav
      .getByRole('menuitem', { name: /user registration/i })
      .first()
      .or(nav.getByRole('link', { name: /user registration/i }).first());

    await expect(userRegItem).toBeVisible();

    await Promise.all([
      page.waitForURL(new RegExp(`${ROUTES.GLOBAL_ADMIN_DASHBOARD}/?$`, 'i')),
      userRegItem.click()
    ]);

    await expect(page).toHaveURL(
      new RegExp(`${ROUTES.GLOBAL_ADMIN_DASHBOARD}/?$`, 'i')
    );

    await expect(
      page.getByRole('heading', {
        name: /global admin dashboard|user registration/i
      })
    ).toBeVisible();
  });
});

test.describe('Home — Global Admin Navigation (responsive)', () => {
  test('Vulnerability Scanning navigates to /VSDashboard', async ({
    pageAsGlobalAdmin
  }) => {
    await clickTopLevelNavAndAssert(
      pageAsGlobalAdmin,
      /vulnerability scanning/i,
      new RegExp(`${ROUTES.VSDASHBOARD}/?$`, 'i'),
      /vulnerability scanning/i
    );
  });

  test('Findings Library navigates to /inventory', async ({
    pageAsGlobalAdmin
  }) => {
    await clickTopLevelNavAndAssert(
      pageAsGlobalAdmin,
      /findings library/i,
      new RegExp(`${ROUTES.INVENTORY}/?$`, 'i'),
      /findings library|inventory/i
    );
  });
});

test.describe('Home — Global Admin: Learning Center nav', () => {
  test('Learning Center expands and shows expected items', async ({
    pageAsGlobalAdmin
  }) => {
    const nav = await navFromHome(pageAsGlobalAdmin);
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
    pageAsGlobalAdmin
  }) => {
    const nav = await navFromHome(pageAsGlobalAdmin);
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
    pageAsGlobalAdmin
  }) => {
    const CISA_RX = /^https:\/\/(www\.)?cisa\.gov\/?$/;
    await assertLearningCenterExternalLink(
      pageAsGlobalAdmin,
      /cisa resources/i,
      CISA_RX
    );
  });
});

test.describe('Home — Global Admin: Support nav', () => {
  test('Support expands and shows expected items', async ({
    pageAsGlobalAdmin
  }) => {
    const nav = await navFromHome(pageAsGlobalAdmin);
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
    pageAsGlobalAdmin
  }) => {
    const nav = await navFromHome(pageAsGlobalAdmin);

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
    pageAsGlobalAdmin
  }) => {
    await assertSupportMailto(pageAsGlobalAdmin, /general questions/i);
  });

  test('Support → Report Bug is a mailto link', async ({
    pageAsGlobalAdmin
  }) => {
    await assertSupportMailto(pageAsGlobalAdmin, /report bug/i);
  });

  test('Support → Send Feedback is a mailto link', async ({
    pageAsGlobalAdmin
  }) => {
    await assertSupportMailto(pageAsGlobalAdmin, /send feedback/i);
  });
});

test.describe('Home — Global Admin: My Account Navigation', () => {
  test('Account Settings navigates to Account Settings', async ({
    pageAsGlobalAdmin
  }) => {
    const nav = await navFromHome(pageAsGlobalAdmin);

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
      pageAsGlobalAdmin.waitForURL(new RegExp(`${ROUTES.SETTINGS}/?$`, 'i'), {
        timeout: 10_000
      }),
      accountSettings.click()
    ]);

    await expect(pageAsGlobalAdmin).toHaveURL(
      new RegExp(`${ROUTES.SETTINGS}/?$`, 'i')
    );
    await expect(
      pageAsGlobalAdmin.getByRole('heading', { name: /my account/i })
    ).toBeVisible();
  });

  test('Logout logs the user out and shows the sign-in page', async ({
    pageAsGlobalAdmin
  }) => {
    await assertLogoutShowsSignIn(pageAsGlobalAdmin);
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
