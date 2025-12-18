import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import { ROUTES } from '../../../frontend/src/constants/routes';
import {
  navFromHome,
  openLearningCenter,
  openSupport,
  clickTopLevelNavAndAssert,
  assertSupportMailto,
  assertLearningCenterExternalLink,
  assertLogoutShowsSignIn
} from '../../utils/navigation_bar';

const IS_CI =
  (process.env.CI ?? '').toLowerCase() === 'true' || process.env.CI === '1';

test.describe('Home — Standard User Navigation (responsive)', () => {
  test.fixme(IS_CI, 'TODO: CI environment missing required data');
  test('Vulnerability Scanning navigates to /VSDashboard', async ({
    pageAsStandardUser
  }) => {
    await clickTopLevelNavAndAssert(
      pageAsStandardUser,
      /vulnerability scanning/i,
      new RegExp(`${ROUTES.VSDASHBOARD}/?$`, 'i'),
      /vulnerability scanning/i
    );
  });

  test('Findings Library navigates to /inventory', async ({
    pageAsStandardUser
  }) => {
    await clickTopLevelNavAndAssert(
      pageAsStandardUser,
      /findings library/i,
      new RegExp(`${ROUTES.INVENTORY}/?$`, 'i'),
      /findings library|inventory/i
    );
  });
});

test.describe('Home — Standard User: Learning Center nav', () => {
  test.fixme(IS_CI, 'TODO: CI environment missing required data');
  test('Learning Center expands and shows expected items', async ({
    pageAsStandardUser
  }) => {
    const nav = await navFromHome(pageAsStandardUser);
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
    pageAsStandardUser
  }) => {
    const nav = await navFromHome(pageAsStandardUser);
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
    pageAsStandardUser
  }) => {
    const CISA_RX = /^https:\/\/(www\.)?cisa\.gov(\/.*)?$/;

    await assertLearningCenterExternalLink(
      pageAsStandardUser,
      /cisa resources/i,
      CISA_RX
    );
  });
});

test.describe('Home — Standard User: Support nav', () => {
  test.fixme(IS_CI, 'TODO: CI environment missing required data');
  test('Support expands and shows expected items', async ({
    pageAsStandardUser
  }) => {
    const nav = await navFromHome(pageAsStandardUser);
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
    pageAsStandardUser
  }) => {
    const nav = await navFromHome(pageAsStandardUser);

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
    pageAsStandardUser
  }) => {
    await assertSupportMailto(pageAsStandardUser, /general questions/i);
  });

  test('Support → Report Bug is a mailto link', async ({
    pageAsStandardUser
  }) => {
    await assertSupportMailto(pageAsStandardUser, /report bug/i);
  });

  test('Support → Send Feedback is a mailto link', async ({
    pageAsStandardUser
  }) => {
    await assertSupportMailto(pageAsStandardUser, /send feedback/i);
  });
});

test.describe('Home — Standard User: My Account Navigation', () => {
  test.fixme(IS_CI, 'TODO: CI environment missing required data');
  test('Account Settings navigates to Account Settings', async ({
    pageAsStandardUser
  }) => {
    const nav = await navFromHome(pageAsStandardUser);

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
      pageAsStandardUser.waitForURL(new RegExp(`${ROUTES.SETTINGS}/?$`, 'i'), {
        timeout: 10_000
      }),
      accountSettings.click()
    ]);

    await expect(pageAsStandardUser).toHaveURL(
      new RegExp(`${ROUTES.SETTINGS}/?$`, 'i')
    );
    await expect(
      pageAsStandardUser.getByRole('heading', { name: /my account/i })
    ).toBeVisible();
  });

  test('Logout logs the user out and shows the sign-in page', async ({
    pageAsStandardUser
  }) => {
    await assertLogoutShowsSignIn(pageAsStandardUser);
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
