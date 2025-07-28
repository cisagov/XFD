import { test, expect } from '../../axe-test';
import type { TestInfo } from '@playwright/test';

test.describe('home', () => {
  test('Test homepage accessibility', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await page.goto('/');
    const results = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(results, null, 2),
      contentType: 'application/json'
    });

    expect(results.violations).toHaveLength(0);
  });
});
