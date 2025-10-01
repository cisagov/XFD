import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';

test.describe('VS Dashboard — Detected Hosts & Top Vulnerable Hosts', () => {
  const hostMetrics = [
    'Detected Hosts',
    'Vulnerable Hosts',
    'Hosts with Unsupported Software'
  ];

  for (const label of hostMetrics) {
    test.skip(`should show "${label}" button with number`, async ({
      page: pageAsGlobalAdmin
    }) => {
      await pageAsGlobalAdmin.goto('/VSDashboard', {
        waitUntil: 'networkidle'
      });
      await pageAsGlobalAdmin.waitForSelector('text=Detected Hosts', {
        timeout: 60000
      });

      const allButtons = pageAsGlobalAdmin.getByRole('button', {
        name: `More information about ${label}`
      });
      const count = await allButtons.count();
      let metricButton = allButtons.first();
      for (let i = 0; i < count; i++) {
        const candidate = allButtons.nth(i);
        const text = await candidate.innerText();
        if (text.match(/\d+/)) {
          metricButton = candidate;
          break;
        }
      }
      await expect(metricButton).toBeVisible();
      const innerText = await metricButton.innerText();
      const number = parseInt(innerText.match(/\d+/)?.[0] ?? '-1', 10);
      expect(Number.isInteger(number)).toBe(true);
      expect(number).toBeGreaterThanOrEqual(0);
    });
  }
});
