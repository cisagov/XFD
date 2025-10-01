import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';

test.describe('Latest Scanning Summary - Page Resize', () => {
  test.skip('Widget is responsive and reload-safe', async ({
    page: pageAsGlobalAdmin
  }) => {
    await pageAsGlobalAdmin.goto('/VSDashboard');
    const widget = pageAsGlobalAdmin
      .getByRole('heading', { name: 'Latest Scanning Summary' })
      .locator('..')
      .locator('..');
    await expect(widget).toBeVisible();
    const infoIcon = widget.getByRole('button', {
      name: /More information about Latest Scanning Summary/i
    });
    if (await infoIcon.isVisible()) {
      await infoIcon.hover();
      const tooltip = pageAsGlobalAdmin.getByRole('tooltip');
      await expect(tooltip).toBeVisible();
    }
    const sizes = [
      { width: 1440, height: 900 },
      { width: 1024, height: 768 },
      { width: 768, height: 600 }
    ];
    for (const size of sizes) {
      await pageAsGlobalAdmin.setViewportSize(size);
      await expect(widget).toBeVisible();
    }
    await pageAsGlobalAdmin.reload();
    await pageAsGlobalAdmin.waitForSelector('text=Latest Scanning Summary');
    await expect(widget).toBeVisible();
  });
});

test.describe('Latest Scanning Summary - ARIA labels', () => {
  test.skip('ARIA: Info icon and metric buttons have correct labels', async ({
    page: pageAsGlobalAdmin
  }) => {
    await pageAsGlobalAdmin.goto('/VSDashboard');

    const infoButton = pageAsGlobalAdmin.getByRole('button', {
      name: 'More information about Latest Scanning Summary'
    });
    await expect(
      infoButton,
      'Info icon for Latest Scanning Summary not found'
    ).toBeVisible();

    const expectedSuffixes = ['Detected KEVs', 'Detected Vulnerabilities'];

    for (const suffix of expectedSuffixes) {
      const regex = new RegExp(`\\d+ ${suffix}`);
      const button = pageAsGlobalAdmin.getByRole('button', { name: regex });
      await expect(
        button,
        `Missing or invisible button with aria-label matching: "${regex}"`
      ).toBeVisible();
    }
  });
});

test.describe('Latest Scanning Summary - Scan Date Display', () => {
  test.skip('should display valid scan date ranges in correct format', async ({
    pageAsGlobalAdmin
  }) => {
    await pageAsGlobalAdmin.goto('/VSDashboard');

    await pageAsGlobalAdmin
      .getByRole('heading', { name: 'Latest Scanning Summary' })
      .waitFor();

    // Find all visible text nodes that look like date ranges
    const dateElements = pageAsGlobalAdmin.getByText(
      /[A-Za-z]{3,9} \d{1,2}, \d{4} - [A-Za-z]{3,9} \d{1,2}, \d{4}/
    );

    const dateTexts = await dateElements.allTextContents();
    expect(dateTexts.length).toBeGreaterThanOrEqual(1);

    const dateRangeRegex =
      /^[A-Za-z]{3,9} \d{1,2}, \d{4} - [A-Za-z]{3,9} \d{1,2}, \d{4}$/;

    for (const text of dateTexts) {
      expect(text).toMatch(dateRangeRegex);
    }
  });
});

test.describe('Latest Scanning Summary Button Tests', () => {
  test.skip('Widget info icon shows correct tooltip', async ({
    page: pageAsGlobalAdmin
  }) => {
    await pageAsGlobalAdmin.goto('/VSDashboard');

    const infoIcon = pageAsGlobalAdmin
      .getByRole('heading', { name: 'Latest Scanning Summary' })
      .locator('..')
      .getByRole('button', {
        name: 'More information about Latest Scanning Summary'
      });

    await infoIcon.hover();
    const tooltip = pageAsGlobalAdmin.getByRole('tooltip');
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toContainText(
      'The Vulnerability Scanning process occurs continuously; any hosts determined to have vulnerabilities are scanned at least once every two weeks and scanned more or less frequently depending on the severity level of the vulnerability finding. If no hosts are found on an asset, the asset will be re-scanned in 90 days. For more information, see Learning Center resources.'
    );
  });

  const metricTooltips = {
    'Detected KEVs':
      'Number of Known Exploited Vulnerabilities found in a scan. KEVS are publicly known vulnerabilities confirmed to be actively exploited by threat actors. See CISA’s Known Exploited Vulnerabilities Catalog for more information.',
    'Detected Vulnerabilities':
      'Total number of vulnerabilities found in a scan, including all occurrences across hosts, ports, and services. False positives are excluded.'
  };

  const redirectingMetrics = new Set([
    'Detected KEVs',
    'Detected Vulnerabilities'
  ]);

  for (const label of Object.keys(metricTooltips)) {
    test.skip(`Click 2 behavior for "${label}" metric card`, async ({
      page: pageAsGlobalAdmin
    }) => {
      const id = label.replace(/\s+/g, '-').toLowerCase();
      await pageAsGlobalAdmin.goto('/VSDashboard');

      // Match buttons like "63 Detected KEVs" or "83 Detected Vulnerabilities"
      const pattern = new RegExp(
        `^\\d+\\s+${label.replace(/\s+/g, '\\s+')}$`,
        'i'
      );
      const buttons = pageAsGlobalAdmin.getByRole('button', { name: pattern });

      const count = await buttons.count();
      let metricButton = buttons.first();
      for (let i = 0; i < count; i++) {
        const btn = buttons.nth(i);
        const text = await btn.innerText();
        if (text.match(/\d+/)) {
          metricButton = btn;
          break;
        }
      }

      await metricButton.click();
      if (redirectingMetrics.has(label)) {
        await expect(pageAsGlobalAdmin).toHaveURL(
          /\/inventory\/vulnerabilities$/
        );
      } else {
        const isFocused = await metricButton.evaluate(
          (el) => document.activeElement === el
        );
        expect(isFocused).toBe(true);
      }
    });
  }
});

test.describe('Latest Scanning Summary - Keyboard Movement', () => {
  test.skip('Keyboard navigation inside widget is tabbable', async ({
    page: pageAsGlobalAdmin
  }) => {
    await pageAsGlobalAdmin.goto('/VSDashboard');

    const widgetContainer = pageAsGlobalAdmin
      .getByRole('heading', { name: 'Latest Scanning Summary' })
      .locator('..')
      .locator('..');
    const infoButton = widgetContainer.getByRole('button', {
      name: /More information about Latest Scanning Summary/i
    });
    await infoButton.focus();

    const getFocusInfo = async () =>
      await pageAsGlobalAdmin.evaluate(() => {
        const el = document.activeElement;
        return {
          tag: el?.tagName,
          role: el?.getAttribute('role'),
          label: el?.getAttribute('aria-label'),
          text: el?.textContent?.trim()
        };
      });

    const focusItems: string[] = [];
    for (let i = 0; i < 6; i++) {
      await pageAsGlobalAdmin.keyboard.press('Tab');
      const info = await getFocusInfo();
      if (info?.label || info?.text) {
        focusItems.push((info.label || info.text)!);
      }
    }

    expect(focusItems).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/\d+\s*Assets\s*Owned/i),
        expect.stringMatching(/\d+\s*Assets\s*Scanned/i),
        expect.stringMatching(/(?:\d+\s*)?Detected\s*KEVs/i),
        expect.stringMatching(/(?:\d+\s*)?Detected\s*Vulnerabilities/i),
        expect.stringMatching(/(?:\d+\s*)?Distinct\s*Vulnerabilities/i),
        expect.stringMatching(/(?:\d+\s*)?False\s*Positives/i)
      ])
    );
  });
});

test.describe('Latest Scanning Summary - Metric Boxes', () => {
  test.skip('Checks that the metric boxes in the widget number + label + tooltip checks', async ({
    page: pageAsGlobalAdmin
  }) => {
    const pause = (ms: number) => pageAsGlobalAdmin.waitForTimeout(ms);

    await pageAsGlobalAdmin.goto('/VSDashboard');
    await pageAsGlobalAdmin.waitForSelector('text=Latest Scanning Summary');

    const widgetContainer = pageAsGlobalAdmin
      .getByRole('heading', { name: 'Latest Scanning Summary' })
      .locator('..')
      .locator('..');

    const infoButton = widgetContainer.getByRole('button', {
      name: /More information about Latest Scanning Summary/i
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
      pageAsGlobalAdmin.evaluate<FocusInfo>(() => {
        const el = document.activeElement as HTMLElement | null;
        return {
          tag: el?.tagName ?? undefined,
          role: el?.getAttribute('role') ?? undefined,
          label: el?.getAttribute('aria-label') ?? undefined,
          text: el?.textContent?.trim() ?? undefined
        };
      });

    const getTooltipText = async (): Promise<string | undefined> => {
      const roleTooltip = pageAsGlobalAdmin.getByRole('tooltip').first();

      try {
        await roleTooltip.waitFor({ state: 'visible', timeout: 3000 });
        const t = await roleTooltip.innerText();
        const cleaned = t?.replace(/\s+/g, ' ').trim();
        if (cleaned) return cleaned;
      } catch {
        /* fall back */
      }

      await pause(500);
      return pageAsGlobalAdmin.evaluate(() => {
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

    for (let i = 0; i < 6; i++) {
      await pageAsGlobalAdmin.keyboard.press('Tab');
      await pause(800);
      const focused = pageAsGlobalAdmin.locator(':focus');
      if (await focused.count()) {
        await focused.hover({ force: true }).catch(() => {});
      }
      await pause(600);

      const info = await getFocusInfo();
      const focusIndex = i + 1;

      if (focusIndex >= 1 && focusIndex <= 10) {
        const tooltip = await getTooltipText();
        focusItems.push({ index: focusIndex, ...info, tooltip });
        await pause(500);
      }
    }

    const expectedLabelByIndex: Record<number, string> = {
      1: 'Assets Owned',
      2: 'Assets Scanned',
      3: 'Detected KEVs',
      4: 'Detected Vulnerabilities',
      5: 'Distinct Vulnerabilities',
      6: 'False Positives'
    };

    const expectedTooltipByIndex: Record<number, string> = {
      1: 'Total number of assets reported by the organization.',
      2: 'Number of assets or IPs scanned during each scan run.',
      3: 'Number of Known Exploited Vulnerabilities found in a scan. KEVS are publicly known vulnerabilities confirmed to be actively exploited by threat actors. See CISA’s Known Exploited Vulnerabilities Catalog for more information.',
      4: 'Total number of vulnerabilities found in a scan, including all occurrences across hosts, ports, and services. False positives are excluded.',
      5: 'Number of unique vulnerabilities found in a scan. Each type of vulnerability is counted once, even if it is found multiple times.',
      6: 'A finding from CyHy scans marked as a false positive per stakeholder request.'
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

  const redirectingMetrics = new Set([
    'Detected KEVs',
    'Detected Vulnerabilities'
  ]);
  const metricTooltips = {
    'Detected KEVs':
      'Number of Known Exploited Vulnerabilities found in a scan. KEVS are publicly known vulnerabilities confirmed to be actively exploited by threat actors. See CISA’s Known Exploited Vulnerabilities Catalog for more information.',
    'Detected Vulnerabilities':
      'Total number of vulnerabilities found in a scan, including all occurrences across hosts, ports, and services. False positives are excluded.'
  };
});
