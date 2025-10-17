import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import type { Page, TestInfo, Locator } from '@playwright/test';

test.describe('Home Page — Standard User Permissions', () => {
  test('should not display "Admin Hub" button, link, or text', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto('/');

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

    await page.goto('/admin-tools', { waitUntil: 'networkidle' });

    const currentUrl = page.url();

    expect(
      currentUrl.endsWith('/admin-tools'),
      'Standard User should not remain on /admin-tools'
    ).toBeFalsy();

    const forbiddenText = page.getByText(
      /(not authorized|forbidden|access denied|permission denied)/i
    );
    const notFoundText = page.getByText(/(not found|404)/i);

    const hasForbidden = await forbiddenText.count();
    const hasNotFound = await notFoundText.count();
    expect(
      hasForbidden > 0 ||
        hasNotFound > 0 ||
        !currentUrl.endsWith('/admin-tools'),
      'Standard User should see a redirect or forbidden message when visiting /admin-tools'
    ).toBeTruthy();
  });
});

test.describe('Home — Standard User Navigation (responsive)', () => {
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
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto('/');

    await openMobileMenuIfPresent(page);
    const item = await getNavItem(page, /vulnerability scanning/i);
    await expect(
      item,
      'Nav item "Vulnerability Scanning" should be visible'
    ).toBeVisible();

    await Promise.all([page.waitForURL(/\/VSDashboard$/i), item.click()]);

    await expect(page).toHaveURL(/\/VSDashboard$/i);
    await expect(
      page.getByRole('heading', { name: /vulnerability scanning/i })
    ).toBeVisible();
  });

  test('Findings Library navigates to /inventory', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto('/');

    await openMobileMenuIfPresent(page);
    const item = await getNavItem(page, /findings library/i);
    await expect(
      item,
      'Nav item "Findings Library" should be visible'
    ).toBeVisible();

    await Promise.all([page.waitForURL(/\/inventory$/i), item.click()]);

    await expect(page).toHaveURL(/\/inventory$/i);
    await expect(
      page.getByRole('heading', { name: /findings library|inventory/i })
    ).toBeVisible();
  });
});

test.describe('Home — Standard User: Learning Center nav', () => {
  async function openMenuIfCollapsed(page: Page) {
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

  async function navScope(page: Page): Promise<Locator> {
    const dialogNav = page.getByRole('dialog', { name: /navigation menu/i });
    if (await dialogNav.isVisible()) {
      return dialogNav.getByRole('navigation', { name: /main navigation/i });
    }
    return page.getByRole('navigation', { name: /main navigation/i });
  }

  test('Learning Center expands and shows expected items', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto('/');

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
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto('/');

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

test.describe('Home — Standard User: Support nav', () => {
  async function openMenuIfCollapsed(page: Page) {
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

  async function navScope(page: Page): Promise<Locator> {
    const dialogNav = page.getByRole('dialog', { name: /navigation menu/i });
    if (await dialogNav.isVisible()) {
      return dialogNav.getByRole('navigation', { name: /main navigation/i });
    }
    return page.getByRole('navigation', { name: /main navigation/i });
  }

  test('Support expands and shows expected items', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto('/');

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
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto('/');

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

test.describe('Home — Standard User: Account Settings nav', () => {
  async function openMenuIfCollapsed(page: Page) {
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

  async function navScope(page: Page): Promise<Locator> {
    const dialog = page.getByRole('dialog', { name: /navigation menu/i });
    if (await dialog.isVisible()) {
      return dialog.getByRole('navigation', { name: /main navigation/i });
    }
    return page.getByRole('navigation', { name: /main navigation/i });
  }

  test('Account Settings navigates to /settings', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto('/');

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
      page.waitForURL(/\/settings\/?$/i, { timeout: 10_000 }),
      accountSettings.click()
    ]);

    await expect(page).toHaveURL(/\/settings\/?$/i);
    await expect(
      page.getByRole('heading', { name: /my account/i })
    ).toBeVisible();
  });
});

test.describe('VSDashboard — Standard User: Filter permissions', () => {
  test('Filter button opens drawer; Region & Organization are disabled and not expandable', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;
    await page.goto('/VSDashboard');

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
  test('first "View domain details for …" opens /inventory/domain/<uuid>', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;

    await page.goto('/inventory');
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
    const identifier = (match?.[1] ?? '').trim(); // optional content assertion below

    const uuidRoute =
      /\/inventory\/domain\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/?$/i;

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

test.describe('Findings Library — Standard User tables', () => {
  test('Domains tab shows "Domains Table"', async ({ pageAsStandardUser }) => {
    const page = pageAsStandardUser;
    await page.goto('/inventory');

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
    await page.goto('/inventory');

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
  test('shows "Latest Scanning Summary"', async ({ pageAsStandardUser }) => {
    const page = pageAsStandardUser;
    await page.goto('/VSDashboard');

    const summary = page
      .getByRole('heading', { name: /latest scanning summary/i })
      .or(page.getByText(/latest scanning summary/i));

    await expect(
      summary,
      'Expected "Latest Scanning Summary" on VSDashboard'
    ).toBeVisible();
  });
});

test.describe('A11y — Standard User (axe)', () => {
  // Home
  test('Home: no serious/critical violations', async ({
    pageAsStandardUser,
    makeAxeBuilder
  }, ti) => {
    await pageAsStandardUser.goto('/');
    await runAxeAndFailOnSerious(
      pageAsStandardUser,
      makeAxeBuilder,
      ti,
      'Home'
    );
  });

  // VSDashboard
  test('VSDashboard: no serious/critical violations', async ({
    pageAsStandardUser,
    makeAxeBuilder
  }, ti) => {
    await pageAsStandardUser.goto('/VSDashboard');
    await runAxeAndFailOnSerious(
      pageAsStandardUser,
      makeAxeBuilder,
      ti,
      'VSDashboard'
    );
  });

  // Findings Library (/inventory)
  test('Inventory: no serious/critical violations', async ({
    pageAsStandardUser,
    makeAxeBuilder
  }, ti) => {
    await pageAsStandardUser.goto('/inventory');
    await runAxeAndFailOnSerious(
      pageAsStandardUser,
      makeAxeBuilder,
      ti,
      'Inventory'
    );
  });

  // Domain details
  test('Domain details: no serious/critical violations', async ({
    pageAsStandardUser,
    makeAxeBuilder
  }, ti) => {
    const page = pageAsStandardUser;
    await page.goto('/inventory');

    const details = page
      .getByRole('button', { name: /view domain details for/i })
      .or(page.getByRole('link', { name: /view domain details for/i }));

    const count = await details.count();
    test.skip(count === 0, 'No domain details available to open');

    await Promise.all([
      page.waitForURL(/\/inventory\/domain\/[0-9a-f-]{36}\/?$/i, {
        timeout: 10_000
      }),
      details.first().click()
    ]);

    await runAxeAndFailOnSerious(page, makeAxeBuilder, ti, 'Domain Details');
  });

  // Settings (/settings → "My Account")
  test('Settings (My Account): no serious/critical violations', async ({
    pageAsStandardUser,
    makeAxeBuilder
  }, ti) => {
    await pageAsStandardUser.goto('/settings');
    await runAxeAndFailOnSerious(
      pageAsStandardUser,
      makeAxeBuilder,
      ti,
      'Settings / My Account'
    );
  });
});

/* ---------------- helper ---------------- */
async function runAxeAndFailOnSerious(
  page: Page,
  makeAxeBuilder: (page: Page) => any,
  testInfo: TestInfo,
  label: string
) {
  const axe = makeAxeBuilder(page);
  const results = await axe.analyze();

  await testInfo.attach(`${label} — axe-results`, {
    body: JSON.stringify(results, null, 2),
    contentType: 'application/json'
  });

  const bad = results.violations.filter((v: any) =>
    ['serious', 'critical'].includes(v.impact)
  );

  expect(
    bad,
    `${label} a11y violations (serious/critical):\n` +
      JSON.stringify(bad, null, 2)
  ).toHaveLength(0);
}
