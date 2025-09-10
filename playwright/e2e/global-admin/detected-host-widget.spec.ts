import { test, expect } from '../../axe-test';

test.describe('Detected Hosts View Details', () => {
  test('View Details link navigates to /inventory/domains', async ({
    page
  }) => {
    await page.goto('/VSDashboard');
    await page.waitForSelector('text=Detected Hosts');

    const detectedLink = page
      .getByRole('link', { name: 'View Details' })
      .nth(1);
    await Promise.all([
      page.waitForURL('**/inventory/domains'),
      detectedLink.click()
    ]);
    await expect(page).toHaveURL(/\/inventory\/domains$/);
  });
});

test.describe('Detected Hosts Info icon', () => {
  test('Detected Hosts info-icon tooltip matches expected content', async ({
    page
  }) => {
    await page.goto('/VSDashboard');
    await page.waitForSelector('text=Detected Hosts');

    const infoIcon = page
      .getByRole('heading', { name: 'Detected Hosts' })
      .locator('..')
      .getByRole('button', { name: 'More information about Detected Hosts' });
    await infoIcon.hover();
    const tooltip = page.getByRole('tooltip');
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toContainText(
      'Hosts with vulnerabilities or unsupported software pose security risks. Tracking and prioritizing these systems can help reduce exposure and prevent potential breaches.'
    );
  });
});

test.describe('Detected Hosts, Top Vulnerable Hosts Chart', () => {
  test('Top Vulnerable Hosts filters: accessibility, chart behavior, and bar colors', async ({
    page
  }) => {
    await page.goto('/VSDashboard');

    const heading = page.getByRole('heading', { name: 'Top Vulnerable Hosts' });
    const widget = heading.locator('..').locator('..').locator('..');
    const radioGroup = widget.locator(
      '[role="radiogroup"][aria-label="Data selector"]'
    );
    await expect(radioGroup).toBeVisible();

    const radios = radioGroup.locator('[role="radio"]');
    const radioCount = await radios.count();
    expect(radioCount).toBeGreaterThanOrEqual(2);

    const allRadio = radios.nth(0);
    const criticalRadio = radios.nth(1);
    const highRadio = radioCount === 3 ? radios.nth(2) : null;

    const bars = widget.locator(
      'rect[role="button"][aria-label*="vulnerabilities"]'
    );
    const barLabels = widget.locator('text=/\\d+\\.\\d+\\.\\d+\\.\\d+/');

    // === All ===
    await criticalRadio.click();
    await allRadio.click({ force: true });

    const allCount = await barLabels.count();
    const allBarCount = await bars.count();
    expect(allBarCount).toBeGreaterThan(0);
    for (let i = 0; i < allBarCount; i++) {
      const fill = await bars.nth(i).getAttribute('fill');
      expect(fill?.trim().toUpperCase()).toBe('#005288');
    }

    // === Critical ===
    await criticalRadio.click();
    const criticalCount = await barLabels.count();
    expect(criticalCount).toBeLessThanOrEqual(allCount);

    const criticalBarCount = await bars.count();
    for (let i = 0; i < criticalBarCount; i++) {
      const fill = await bars.nth(i).getAttribute('fill');
      expect(fill?.trim().toUpperCase()).toBe('#731A00');
    }

    // === High ===
    if (highRadio) {
      await highRadio.click();
      const highCount = await barLabels.count();
      expect(highCount).toBeLessThanOrEqual(allCount);

      const highBarCount = await bars.count();
      for (let i = 0; i < highBarCount; i++) {
        const fill = await bars.nth(i).getAttribute('fill');
        expect(fill?.trim().toUpperCase()).toBe('#EC7633');
      }
    }
  });
});

test.describe('Detected Hosts, Top Vulnerable Hosts Tooltips', () => {
  test('hovering any Top Vulnerable Hosts chart bar shows its label in a tooltip', async ({
    page
  }) => {
    const pause = (ms: number) => page.waitForTimeout(ms);

    await page.goto('/VSDashboard');
    await pause(800);

    const heading = page.getByRole('heading', { name: 'Top Vulnerable Hosts' });

    const widget = heading.locator('..').locator('..').locator('..');

    const bars = widget.locator(
      'rect[role="button"][aria-label*="vulnerabilities"]'
    );
    const count = await bars.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const bar = bars.nth(i);
      const aria = await bar.getAttribute('aria-label');
      if (!aria) continue;

      const match = aria.match(/Bar\s+(.*?)\s+with/);
      const label = match?.[1];
      if (!label) continue;

      await bar.scrollIntoViewIfNeeded();
      await pause(500);
      await bar.hover();
      await pause(800);

      const tooltip = page.getByRole('tooltip');
      await tooltip.waitFor({ state: 'visible', timeout: 3000 });
      const tooltipText = (await tooltip.textContent())?.trim();
      expect(tooltipText).toContain(label);

      await pause(500);
    }
  });
});

function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

test.describe('Detected Hosts, Top Vulnerable Hosts Navigation', () => {
  test('Clicking Top Vulnerable Hosts chart bar navigates to host detail page', async ({
    page
  }) => {
    await page.goto('/VSDashboard');

    const widget = page
      .getByRole('heading', { name: 'Top Vulnerable Hosts' })
      .locator('..')
      .locator('..')
      .locator('..');

    const barButtons = widget.getByRole('button', {
      name: /Bar .* with \d+ vulnerabilities/i
    });
    const ipTexts = widget.locator('text=/\\b\\d+\\.\\d+\\.\\d+\\.\\d+\\b/');

    const bar = barButtons.first();

    const raw = await ipTexts.first().textContent();
    const expectedIP = (raw ?? '').trim();
    expect(expectedIP).toBeTruthy();

    await Promise.all([page.waitForLoadState('domcontentloaded'), bar.click()]);

    await expect(
      page.getByRole('heading', {
        name: new RegExp(`^${escapeRegExp(expectedIP)}$`)
      })
    ).toBeVisible();
  });
});

test.describe('Detected Hosts ARIA labels', () => {
  test('ARIA: Detected + Top Vulnerable Hosts have correct roles and labels', async ({
    page
  }) => {
    await page.goto('/VSDashboard');
    await page.waitForSelector('text=Detected Hosts');

    // ===== Detected Hosts Section =====
    const detectedHostsHeader = page.getByRole('heading', {
      name: 'Detected Hosts'
    });
    await expect(detectedHostsHeader).toBeVisible();

    const infoButton = detectedHostsHeader
      .locator('..')
      .getByRole('button', { name: /More information about Detected Hosts/i });
    await expect(infoButton).toHaveAttribute(
      'aria-label',
      /More information about Detected Hosts/i
    );

    const viewDetailsLink = detectedHostsHeader
      .locator('..')
      .locator('..')
      .getByRole('link', { name: /View Details/i });
    await expect(viewDetailsLink).toBeVisible();
    await expect(viewDetailsLink).toHaveAttribute('href');

    // ===== Top Vulnerable Hosts Section =====
    const topHostsHeading = page.getByRole('heading', {
      name: 'Top Vulnerable Hosts'
    });
    await expect(topHostsHeading).toBeVisible();

    const widget = topHostsHeading.locator('..').locator('..').locator('..');

    const radioGroup = widget.locator(
      '[role="radiogroup"][aria-label="Data selector"]'
    );
    await expect(radioGroup).toHaveAttribute('role', 'radiogroup');
    await expect(radioGroup).toHaveAttribute('aria-label', 'Data selector');

    // ===== IP Bars =====
    const bars = widget.locator(
      'rect[role="button"][aria-label*="vulnerabilities"]'
    );
    const barCount = await bars.count();
    expect(barCount).toBeGreaterThan(0);

    for (let i = 0; i < barCount; i++) {
      const bar = bars.nth(i);
      await expect(bar).toHaveAttribute('role', 'button');
      await expect(bar).toHaveAttribute(
        'aria-label',
        /Bar .* vulnerabilities/i
      );
    }
  });
});

test.describe('Detected Hosts Keyboard Movement', () => {
  test('Keyboard navigation traverses Detected Hosts widget', async ({
    page
  }) => {
    await page.goto('/VSDashboard');
    await page.getByRole('heading', { name: 'Detected Hosts' }).waitFor();

    const widgetContainer = page
      .getByRole('heading', { name: 'Detected Hosts' })
      .locator('..')
      .locator('..');

    const infoButton = widgetContainer.getByRole('button', {
      name: /More information about Detected Hosts/i
    });
    await infoButton.focus();
    await page.waitForTimeout(500);

    const normalize = (s: string) =>
      s
        .replace(/\s+/g, ' ')
        .replace(/(\d)([A-Za-z])/g, '$1 $2')
        .trim();

    const isNoiseMetric = (s: string) =>
      [
        /^\d+\s*Detected\s*Hosts$/i,
        /^\d+\s*Vulnerable\s*Hosts$/i,
        /^\d+\s*Hosts\s*with\s*Unsupported\s*Software$/i
      ].some((r) => r.test(s));

    const getFocusInfo = async () =>
      widgetContainer.evaluate((container) => {
        const el = document.activeElement as HTMLElement | null;
        const inside = !!(el && container.contains(el));
        const label = el?.getAttribute('aria-label') ?? '';
        const text = el?.textContent ?? '';
        return { inside, label, text };
      });

    const focusItems: string[] = [];
    for (let i = 0; i < 10; i++) {
      const { inside, label, text } = await getFocusInfo();
      const value = normalize(label || text || '');
      if (value && !isNoiseMetric(value)) focusItems.push(value);
      await page.keyboard.press('Tab');
    }

    expect(focusItems).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/More information about Detected Hosts/i),
        expect.stringMatching(/View Details/i),
        expect.stringMatching(/\b(All|Critical|High|Medium|Low)\b/i)
      ])
    );

    const sawBar = focusItems.some((t) => /Bar .* vulnerabilities/i.test(t));
  });
});

test.describe('Detected Hosts Metric Boxes', () => {
  test('Checks that the metric boxes in the widget number + label + tooltip checks', async ({
    page
  }) => {
    const pause = (ms: number) => page.waitForTimeout(ms);

    await page.goto('/VSDashboard');
    await page.waitForSelector('text=Detected Hosts');

    const widgetContainer = page
      .getByRole('heading', { name: 'Detected Hosts' })
      .locator('..')
      .locator('..');

    const infoButton = widgetContainer.getByRole('button', {
      name: /More information about Detected Hosts/i
    });

    await infoButton.focus();
    await pause(800);
    await infoButton.hover();
    await pause(600);

    type FocusInfo = {
      tag?: string;
      role?: string;
      label?: string;
      text?: string;
    };

    const getFocusInfo = async (): Promise<FocusInfo> =>
      page.evaluate<FocusInfo>(() => {
        const el = document.activeElement as HTMLElement | null;
        return {
          tag: el?.tagName ?? undefined,
          role: el?.getAttribute('role') ?? undefined,
          label: el?.getAttribute('aria-label') ?? undefined,
          text: el?.textContent?.trim() ?? undefined
        };
      });

    const getTooltipText = async (): Promise<string | undefined> => {
      const roleTooltip = page.getByRole('tooltip').first();

      try {
        await roleTooltip.waitFor({ state: 'visible', timeout: 3000 });
        const t = await roleTooltip.innerText();
        const cleaned = t?.replace(/\s+/g, ' ').trim();
        if (cleaned) return cleaned;
      } catch {
        /* fall back */
      }

      await pause(500);
      return page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        const ids = (
          el?.getAttribute('aria-describedby') ||
          el?.getAttribute('aria-details')
        )?.trim();
        if (!ids) return undefined;
        const combined = ids
          .split(/\s+/)
          .map((id) => document.getElementById(id)?.textContent?.trim())
          .filter((s): s is string => !!s && s.length > 0)
          .join(' ');
        return combined.replace(/\s+/g, ' ').trim() || undefined;
      });
    };

    const normalizeForLabelCheck = (s?: string) =>
      (s ?? '')
        .replace(/\d+/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .replace(/\s+/g, ' ')
        .trim();

    const makeWordBoundaryRegex = (expected: string) => {
      const words = expected
        .trim()
        .split(/\s+/)
        .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
      return new RegExp(words.map((w) => `\\b${w}\\b`).join('\\s+'), 'i');
    };

    const focusItems: Array<{
      index: number;
      tag?: string;
      role?: string;
      label?: string;
      text?: string;
      tooltip?: string;
    }> = [];

    for (let i = 0; i < 4; i++) {
      await page.keyboard.press('Tab');
      await pause(800);
      const focused = page.locator(':focus');
      if (await focused.count()) {
        await focused.hover({ force: true }).catch(() => {});
      }
      await pause(600);

      const info = await getFocusInfo();
      const focusIndex = i + 1;

      if (focusIndex >= 2 && focusIndex <= 4) {
        const tooltip = await getTooltipText();
        focusItems.push({ index: focusIndex, ...info, tooltip });
        await pause(500);
      }
    }

    const expectedLabelByIndex: Record<number, string> = {
      2: 'Detected Hosts',
      3: 'Vulnerable Hosts',
      4: 'Hosts with Unsupported Software'
    };

    const expectedTooltipByIndex: Record<number, string> = {
      2: 'Total number of hosts identified during the most recent scan.',
      3: 'Hosts with at least one vulnerability detected during the most recent scan.',
      4: 'Software that no longer receives updates, including new features, bug fixes, or security patches for newly discovered vulnerabilities, making it more susceptible to security threats.'
    };

    for (const item of focusItems) {
      const idx = item.index;
      const rawText = item.label || item.text || '';

      if (!/\d/.test(rawText)) {
        throw new Error(
          `Index ${idx} text must include a number. Got: "${rawText}"`
        );
      }

      const cleanedLabel = normalizeForLabelCheck(rawText);
      expect(cleanedLabel).toMatch(
        makeWordBoundaryRegex(expectedLabelByIndex[idx])
      );

      const normalizedTooltip = item.tooltip?.replace(/\s+/g, ' ').trim() ?? '';
      expect(normalizedTooltip).toContain(expectedTooltipByIndex[idx]);
    }
  });
});
