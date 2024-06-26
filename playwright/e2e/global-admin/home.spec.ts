import { describe } from 'node:test';

const { test, expect, Page } = require('../../axe-test');

test.describe.configure({ mode: 'parallel' });
let page: InstanceType<typeof Page>;

test.describe('home', () => {
  test.beforeEach(async ({ browser }) => {
    const context = await browser.newContext();
    page = await context.newPage();
    await page.goto('/');
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('Test homepage accessibility', async ({
    page,
    makeAxeBuilder
  }, testInfo) => {
    const accessibilityScanResults = await makeAxeBuilder().analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });
});
