import { expect } from '@playwright/test';
import type { Page, Locator } from '@playwright/test';
import { openMenuIfCollapsed, navScope } from './menu_collapse';
import { ROUTES } from '../../frontend/src/constants/routes';

export async function navFromHome(page: Page): Promise<Locator> {
  await page.goto(ROUTES.HOME);
  await openMenuIfCollapsed(page);
  return navScope(page);
}

export async function openDropdown(
  nav: Locator,
  labelRx: RegExp,
  labelText: string
): Promise<Locator> {
  const toggle = nav.getByRole('button', { name: labelRx }).first();
  await expect(toggle, `${labelText} toggle should exist`).toBeVisible();

  if ((await toggle.getAttribute('aria-expanded')) !== 'true') {
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  }

  return toggle;
}

export async function openAdminHub(nav: Locator): Promise<Locator> {
  return openDropdown(nav, /^admin hub$/i, 'Admin Hub');
}

export async function openLearningCenter(nav: Locator): Promise<Locator> {
  return openDropdown(nav, /^learning center$/i, 'Learning Center');
}

export async function openSupport(nav: Locator): Promise<Locator> {
  return openDropdown(nav, /^support$/i, 'Support');
}

// Responsive top-nav helpers
export async function openMobileMenuIfPresent(page: Page) {
  const trigger = page
    .getByRole('button', { name: /menu|open.*menu|navigation/i })
    .first();
  if (await trigger.isVisible().catch(() => false)) {
    await trigger.click();
    await expect(
      page.getByRole('dialog', { name: /navigation menu/i })
    ).toBeVisible();
  }
}

export async function getNavItem(page: Page, nameRx: RegExp): Promise<Locator> {
  const navDialog = page.getByRole('dialog', { name: /navigation menu/i });
  if (await navDialog.isVisible().catch(() => false)) {
    return navDialog.getByRole('menuitem', { name: nameRx });
  }

  const mainNav = page.getByRole('navigation', { name: /main navigation/i });
  const link = mainNav.getByRole('link', { name: nameRx });
  if (await link.count()) return link;

  const btn = mainNav.getByRole('button', { name: nameRx });
  if (await btn.count()) return btn;

  return page.getByText(nameRx, { exact: false });
}

export async function clickTopLevelNavAndAssert(
  page: Page,
  labelRx: RegExp,
  urlRx: RegExp,
  headingRx: RegExp
) {
  await page.goto(ROUTES.HOME);
  await openMobileMenuIfPresent(page);

  const item = await getNavItem(page, labelRx);
  await expect(item, `Nav item "${labelRx}" should be visible`).toBeVisible();

  await Promise.all([page.waitForURL(urlRx), item.click()]);

  await expect(page).toHaveURL(urlRx);
  await expect(page.getByRole('heading', { name: headingRx })).toBeVisible();
}

export async function assertSupportMailto(page: Page, itemRx: RegExp) {
  const nav = await navFromHome(page);
  await openSupport(nav);

  const link = nav
    .getByRole('link', { name: itemRx })
    .first()
    .or(nav.getByRole('menuitem', { name: itemRx }).first());

  await expect(
    link,
    `Support item "${itemRx}" should be visible`
  ).toBeVisible();

  const href = await link.getAttribute('href');
  expect(href, 'Support link should have an href').toBeTruthy();
  expect(
    href?.startsWith('mailto:'),
    `Expected a mailto: link, got href="${href}"`
  ).toBeTruthy();

  await link.click();
}

export async function assertLearningCenterExternalLink(
  page: Page,
  itemRx: RegExp,
  hrefRx: RegExp
) {
  const nav = await navFromHome(page);
  await openLearningCenter(nav);

  const link = nav
    .getByRole('link', { name: itemRx })
    .first()
    .or(nav.getByRole('menuitem', { name: itemRx }).first());

  await expect(
    link,
    `"${itemRx}" item should be visible in Learning Center menu`
  ).toBeVisible();

  const href = await link.getAttribute('href');
  expect(href, 'Learning Center link should have an href').toBeTruthy();
  expect(
    hrefRx.test(href ?? ''),
    `Expected href to match ${hrefRx}, got "${href}"`
  ).toBeTruthy();

  await link.click();
}

export async function assertLogoutShowsSignIn(page: Page) {
  const nav = await navFromHome(page);

  const myAccountToggle = nav
    .getByRole('button', { name: /^my account$/i })
    .first();
  const hasMyAccountToggle = await myAccountToggle
    .isVisible()
    .catch(() => false);

  let logoutItem: Locator;

  if (hasMyAccountToggle) {
    if ((await myAccountToggle.getAttribute('aria-expanded')) !== 'true') {
      await myAccountToggle.click();
      await expect(myAccountToggle).toHaveAttribute('aria-expanded', 'true');
    }

    logoutItem = nav
      .getByRole('menuitem', { name: /logout/i })
      .first()
      .or(nav.getByRole('link', { name: /logout/i }).first());
  } else {
    logoutItem = nav
      .getByRole('link', { name: /logout/i })
      .first()
      .or(nav.getByRole('menuitem', { name: /logout/i }).first());
  }

  await expect(
    logoutItem,
    '"Logout" item should be visible in navigation'
  ).toBeVisible();

  await Promise.all([
    page.waitForLoadState('domcontentloaded'),
    logoutItem.click()
  ]);

  await expect(
    page.getByRole('heading', { name: /welcome to cyhy dashboard/i })
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: /sign in with login.gov/i })
  ).toBeVisible();
  await expect(page.getByRole('button', { name: /^my account$/i })).toHaveCount(
    0
  );
}

// Existing helper, kept as-is
export async function getNamedTable(
  page: Page,
  nameRx: RegExp
): Promise<Locator> {
  const table = page.getByRole('table', { name: nameRx });
  if (await table.count()) return table.first();

  const grid = page.getByRole('grid', { name: nameRx });
  if (await grid.count()) return grid.first();

  const generic = page.getByRole('generic', { name: nameRx });
  if (await generic.count()) return generic.first();

  return page.getByLabel(nameRx).first();
}
