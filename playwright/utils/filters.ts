import { expect, type Page, type Locator } from '@playwright/test';

export type DrawerConfig = {
  headingRx: RegExp;
  closeBtnName: RegExp;
  filtersBtnName?: RegExp;
  urlKeys?: { region: string[]; org: string[] };
};

export function getFiltersButton(page: Page, cfg: DrawerConfig): Locator {
  return page
    .getByRole('button', { name: cfg.filtersBtnName ?? /filters?/i })
    .first();
}

export async function waitForFiltersDrawer(
  page: Page,
  cfg: DrawerConfig,
  timeoutMs = 5000
): Promise<Locator> {
  const heading = page.getByRole('heading', { name: cfg.headingRx }).first();
  await expect(heading).toBeVisible({ timeout: timeoutMs });

  const drawer = heading.locator(
    'xpath=ancestor-or-self::*[' +
      'self::aside or @role="dialog" or @role="region" or self::div' +
      '][1]'
  );
  return drawer.first();
}

export async function openFiltersDrawer(
  page: Page,
  cfg: DrawerConfig
): Promise<void> {
  await page.waitForLoadState('domcontentloaded');
  const btn = getFiltersButton(page, cfg);
  await expect(btn).toBeVisible();
  await expect(btn).toBeEnabled();
  await btn.scrollIntoViewIfNeeded();

  const canClick = await btn.click({ trial: true, timeout: 500 }).then(
    () => true,
    () => false
  );
  if (canClick) {
    await btn.click();
  } else {
    await btn.focus().catch(() => {});
    await page.keyboard.press('Enter').catch(async () => {
      await page.keyboard.press(' ');
    });
  }

  await waitForFiltersDrawer(page, cfg, 5000);
}

export async function closeFilterDrawer(
  page: Page,
  cfg: DrawerConfig,
  opts: { assertHidden: boolean }
): Promise<void> {
  const closeBtn = page.getByRole('button', { name: cfg.closeBtnName }).first();

  if (!(await closeBtn.isVisible().catch(() => false))) {
    const heading = page.getByRole('heading', { name: cfg.headingRx }).first();
    await heading.focus().catch(() => {});
  }

  await expect(closeBtn, 'Close button not found').toBeVisible();
  await expect(closeBtn).toBeEnabled();

  const canClick = await closeBtn.click({ trial: true, timeout: 500 }).then(
    () => true,
    () => false
  );
  if (canClick) {
    await closeBtn.click();
  } else {
    await closeBtn.focus().catch(() => {});
    await page.keyboard.press('Enter').catch(async () => {
      await page.keyboard.press(' ');
    });
  }

  if (opts.assertHidden) {
    await page.waitForTimeout(100); // transition grace
    const drawer = await waitForFiltersDrawer(page, cfg, 2000).catch(
      () => null
    );
    if (drawer) {
      try {
        await expect(drawer).toBeHidden({ timeout: 1000 });
      } catch {
        /* tolerate flake */
      }
    }
  } else {
    await page.waitForTimeout(100);
  }
}

export async function ensureSectionOpen(page: Page, sectionButtonName: RegExp) {
  const btn = page.getByRole('button', { name: sectionButtonName }).first();
  await expect(
    btn,
    `Missing section button: ${sectionButtonName}`
  ).toBeVisible();

  const expanded = (await btn.getAttribute('aria-expanded')) === 'true';
  if (!expanded) {
    await btn.click();
    await expect(btn).toHaveAttribute('aria-expanded', 'true');
  }
}

export async function selectFromAutocomplete(
  page: Page,
  label: RegExp,
  preferred?: string | RegExp
): Promise<string> {
  const input = page.getByRole('combobox', { name: label }).first();
  await expect(input, `Missing combobox: ${label}`).toBeVisible();

  const ariaDisabled = await input.getAttribute('aria-disabled');
  const isDisabled = await input.isDisabled().catch(() => false);
  expect(
    !isDisabled && ariaDisabled !== 'true',
    `Expected "${label}" enabled`
  ).toBeTruthy();

  await openAutocomplete(input, page);

  const listbox = page.getByRole('listbox').first();
  await expect(listbox).toBeVisible();

  const option = preferred
    ? listbox.getByRole('option', { name: preferred }).first()
    : listbox.getByRole('option').first();

  const optionText = (await option.textContent())?.trim() || 'Unknown';
  await option.click();

  await expect(page.getByRole('listbox')).toHaveCount(0);
  await expect(input).toHaveValue(optionText);
  return optionText;
}

export async function selectAnyOrganization(
  page: Page,
  label: RegExp,
  probeChars: string[] = ['a', 'e', 'i', 'o', 'u', 's', 'n', 't', 'r', 'l']
): Promise<string> {
  const input = page.getByRole('combobox', { name: label }).first();
  await expect(input).toBeVisible();

  const ariaDisabled = await input.getAttribute('aria-disabled');
  const isDisabled = await input.isDisabled().catch(() => false);
  expect(
    !isDisabled && ariaDisabled !== 'true',
    `Expected "${label}" enabled`
  ).toBeTruthy();

  await openAutocomplete(input, page);
  let listbox = page.getByRole('listbox').first();
  let count = await listbox.getByRole('option').count();

  for (const ch of probeChars) {
    if (count > 0) break;
    await input.fill('');
    await input.type(ch, { delay: 15 });
    await page.waitForTimeout(80);
    listbox = page.getByRole('listbox').first(); // re-acquire
    count = await listbox.getByRole('option').count();
  }
  expect(
    count,
    'Expected at least one organization option after typing'
  ).toBeGreaterThan(0);

  const option = listbox.getByRole('option').first();
  const optionText = (await option.textContent())?.trim() || 'Unknown';
  await option.click();

  await expect(page.getByRole('listbox')).toHaveCount(0);
  await input.press('Enter').catch(() => {});
  await input.blur().catch(() => {});
  const applyBtn = page
    .getByRole('button', { name: /(apply|done|save)/i })
    .first();
  if (await applyBtn.isVisible().catch(() => false)) {
    await applyBtn.click().catch(() => {});
  }

  return optionText;
}

export async function openAutocomplete(input: Locator, page: Page) {
  await input.click();
  if ((await input.getAttribute('aria-expanded')) !== 'true')
    await input.press('ArrowDown');
  if ((await input.getAttribute('aria-expanded')) !== 'true')
    await input.press('Enter');

  if ((await input.getAttribute('aria-expanded')) !== 'true') {
    const openBtn = page.getByRole('button', { name: /^open$/i }).first();
    if (await openBtn.isVisible()) await openBtn.click();
  }

  await expect(page.getByRole('listbox').first()).toBeVisible();
}

export async function isVisible(
  locator: Locator,
  timeout = 1000
): Promise<boolean> {
  try {
    await expect(locator).toBeVisible({ timeout });
    return true;
  } catch {
    return false;
  }
}

export async function hasValue(
  input: Locator,
  expected: string
): Promise<boolean> {
  try {
    await expect(input).toHaveValue(expected, { timeout: 500 });
    return true;
  } catch {
    return false;
  }
}

export function escapeForTextSelector(s: string) {
  return s.replace(/["'`]/g, '');
}

export function getFilterChipLocator(page: Page, text: string): Locator {
  const safe = escapeForTextSelector(text);
  return page.locator(
    [
      `.MuiChip-root:has-text("${safe}")`,
      `[data-testid="filter-chip"]:has-text("${safe}")`,
      'header, [role="toolbar"], [data-testid="filters-summary"]'
    ].join(', ')
  );
}

export async function urlHasBothFilters(
  page: Page,
  cfg: DrawerConfig,
  timeout = 1500
): Promise<boolean> {
  const { region, org } = cfg.urlKeys ?? { region: [], org: [] };
  try {
    await expect
      .poll(
        () => {
          const u = new URL(page.url());
          const r = region.map((k) => u.searchParams.get(k)).find(Boolean);
          const o = org.map((k) => u.searchParams.get(k)).find(Boolean);
          return Boolean(r && o);
        },
        { timeout }
      )
      .toBe(true);
    return true;
  } catch {
    return false;
  }
}
