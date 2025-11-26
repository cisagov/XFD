import { expect, type Page, type Locator } from '@playwright/test';

// Following the same pattern as VSDashRegionAndOrgFilters.tsx component
// This constant matches the allRegionsOption defined there
const allRegionsOption = 'All Regions';

export type DrawerConfig = {
  headingRx: RegExp;
  closeBtnName: RegExp;
  filtersBtnName?: RegExp;
  urlKeys?: { region: string[]; org: string[] };
};

export type AppKind = 'VS' | 'INV';
export const PRESETS: Record<AppKind, DrawerConfig> = {
  VS: {
    headingRx: /^filter$/i,
    closeBtnName: /^close$/i,
    filtersBtnName: /filters?/i,
    urlKeys: {
      region: ['region', 'regionId', 'region_id'],
      org: ['organization', 'orgId', 'organization_id']
    }
  },
  INV: {
    headingRx: /^filter$/i,
    closeBtnName: /^close-filter-drawer$/i,
    filtersBtnName: /filters?/i,
    urlKeys: {
      region: ['region', 'regionId', 'region_id'],
      org: ['organization', 'orgId', 'organization_id']
    }
  }
};

export const VS: DrawerConfig = PRESETS.VS;
export const INV: DrawerConfig = PRESETS.INV;

type AppArg = DrawerConfig | AppKind | undefined;
const toCfg = (arg?: AppArg): DrawerConfig =>
  typeof arg === 'string' ? PRESETS[arg] : (arg ?? PRESETS.VS);

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
  app?: AppArg, // <-- accepts DrawerConfig or "VS" | "INV"
  opts?: { assertHidden?: boolean; timeout?: number }
) {
  const cfg = toCfg(app);
  const timeout = opts?.timeout ?? 5000;

  const canInteract = async (loc: Locator) => {
    if ((await loc.count()) === 0) return false;
    try {
      const el = loc.first();
      if (!(await el.isVisible())) return false;
      if (!(await el.isEnabled())) return false;
      return true;
    } catch {
      return false;
    }
  };

  const heading = page.getByRole('heading', { name: cfg.headingRx }).first();
  const drawer = heading
    .locator(
      'xpath=ancestor-or-self::*[' +
        'self::aside or @role="dialog" or @role="region" or self::div' +
        '][1]'
    )
    .first();

  const drawerExists = (await drawer.count()) > 0;
  const scoped = (sel: string) =>
    drawerExists ? drawer.locator(sel) : page.locator(sel);
  const scopedRole = (role: Parameters<Page['getByRole']>[0], ropts: any) =>
    drawerExists
      ? drawer.getByRole(role as any, ropts)
      : page.getByRole(role as any, ropts);

  const candidates: Locator[] = [
    scoped('[data-testid="close-filter-drawer"]'),
    scoped('#close-filter-drawer'),
    scoped('.close-filter-drawer'),
    scopedRole('button', { name: cfg.closeBtnName }),
    scopedRole('button', { name: /^(close|close filters?|hide filters?)$/i }),
    scopedRole('button', { name: /^(hide|done|apply|dismiss|cancel)$/i }),
    scoped('button[aria-label*="close" i], button[title*="close" i]'),
    page.getByRole('button', { name: /^close$/i })
  ];

  let closedByClick = false;
  for (const loc of candidates) {
    if (await canInteract(loc)) {
      try {
        await loc.first().click({ timeout: 1200 });
        closedByClick = true;
        break;
      } catch {}
    }
  }

  const stillVisible =
    (await drawer.count()) > 0 && (await drawer.isVisible().catch(() => false));

  if (!closedByClick && stillVisible) {
    try {
      await page.keyboard.press('Escape');
    } catch {}

    if (await drawer.isVisible().catch(() => false)) {
      const backdrop = page.locator(
        [
          '.MuiBackdrop-root',
          '.MuiModal-backdrop',
          '[data-overlay="true"]',
          '[role="presentation"]',
          '[data-testid="modal-overlay"]'
        ].join(', ')
      );
      if (await canInteract(backdrop)) {
        try {
          await backdrop.first().click();
        } catch {}
      }
    }

    if (await drawer.isVisible().catch(() => false)) {
      const toggle = page
        .getByRole('button', { name: cfg.filtersBtnName ?? /^filters?$/i })
        .first();
      if (await canInteract(toggle)) {
        try {
          await toggle.click();
        } catch {}
      }
    }
  }

  if (opts?.assertHidden) {
    await expect
      .poll(
        async () => {
          const cnt = await drawer.count();
          if (cnt === 0) return true;
          return !(await drawer.isVisible().catch(() => false));
        },
        { timeout }
      )
      .toBeTruthy();
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
    listbox = page.getByRole('listbox').first();
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

// VS Dashboard specific filter helper functions
// These functions use the robust generic infrastructure while maintaining backward compatibility
export async function openVSFiltersDrawer(page: Page): Promise<void> {
  await openFiltersDrawer(page, VS);
}

export async function closeVSFiltersDrawer(page: Page): Promise<void> {
  await closeFilterDrawer(page, VS);
}

export interface FilterCheckResult {
  region: string;
  org: string;
  hasFilters: boolean;
  regionDisabled?: boolean;
  orgDisabled?: boolean;
  filtersDisabled?: boolean;
}

/**
 * Generic function to check filter states (values and disabled status)
 * @param page - Playwright page object
 * @param cfg - DrawerConfig (defaults to VS)
 * @param checkDisabled - Whether to check disabled status instead of values
 */
export async function checkFilterState(
  page: Page,
  cfg: DrawerConfig = VS,
  checkDisabled: boolean = false
): Promise<FilterCheckResult> {
  await page.waitForLoadState('domcontentloaded');

  const filterBtn = getFiltersButton(page, cfg);

  if (await isVisible(filterBtn, 5000)) {
    try {
      await openFiltersDrawer(page, cfg);

      const regionInput = page
        .getByRole('combobox', { name: /^region$/i })
        .first();
      const orgInput = page
        .getByRole('combobox', { name: /^organization$/i })
        .first();

      if (checkDisabled) {
        // Check disabled status
        const regionDisabled = await regionInput.isDisabled();
        const orgDisabled = await orgInput.isDisabled();

        console.log(
          `Filter status - Region disabled: ${regionDisabled}, Org disabled: ${orgDisabled}`
        );

        await closeFilterDrawer(page, cfg);

        return {
          region: '',
          org: '',
          hasFilters: false,
          regionDisabled,
          orgDisabled,
          filtersDisabled: regionDisabled && orgDisabled
        };
      } else {
        // Check values
        const currentRegionValue = await regionInput.inputValue();
        const currentOrgValue = await orgInput.inputValue();

        console.log(
          `Filter check - Region: "${currentRegionValue}", Org: "${currentOrgValue}"`
        );

        await closeFilterDrawer(page, cfg);

        return {
          region: currentRegionValue,
          org: currentOrgValue,
          hasFilters:
            currentRegionValue !== '' &&
            !currentRegionValue.includes(allRegionsOption) &&
            currentOrgValue !== ''
        };
      }
    } catch (error) {
      console.log(
        'Error checking filters - assuming filters not available',
        error
      );
      return {
        region: '',
        org: '',
        hasFilters: false,
        regionDisabled: true,
        orgDisabled: true,
        filtersDisabled: true
      };
    }
  } else {
    console.log('Filter button not found - assuming filters not available');
    return {
      region: '',
      org: '',
      hasFilters: false,
      regionDisabled: true,
      orgDisabled: true,
      filtersDisabled: true
    };
  }
}

// Convenience wrapper functions for backwards compatibility
export async function checkFiltersHaveValues(
  page: Page
): Promise<FilterCheckResult> {
  return checkFilterState(page, VS, false);
}

export async function checkFiltersDisabled(
  page: Page
): Promise<FilterCheckResult> {
  return checkFilterState(page, VS, true);
}
