import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import type { TestInfo } from '@playwright/test';
import { ROUTES } from '../../../frontend/src/constants/routes';

test.describe('Vulnerabilities', () => {
  test.skip('Test vulnerabilities accessibility', async ({
    page: pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await pageAsGlobalAdmin.goto(ROUTES.VULNERABILITIES);

    const accessibilityScanResults =
      await makeAxeBuilder(pageAsGlobalAdmin).analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  //TODO: Skip this test until the vulnerability table data is loaded in localhost.
  test.skip('Test vulnerability details NIST link', async ({
    page: pageAsGlobalAdmin
  }) => {
    await pageAsGlobalAdmin.goto(ROUTES.VULNERABILITIES);
    const newTabPromise = pageAsGlobalAdmin.waitForEvent('popup');

    await pageAsGlobalAdmin
      .getByRole('row')
      .nth(1)
      .getByRole('cell')
      .nth(0)
      .click();
    const newTab = await newTabPromise;
    await newTab.waitForLoadState();
    await expect(newTab).toHaveURL(
      new RegExp('^https://nvd\\.nist\\.gov/vuln/detail/')
    );
  });

  //TODO: Skip this test until the vulnerability table data is loaded in localhost.
  test.skip('Test domain details link', async ({ page: pageAsGlobalAdmin }) => {
    await pageAsGlobalAdmin.goto(ROUTES.VULNERABILITIES);
    await pageAsGlobalAdmin
      .getByRole('row')
      .nth(1)
      .getByRole('cell')
      .nth(3)
      .click();
    await expect(pageAsGlobalAdmin).toHaveURL(
      new RegExp(ROUTES.DOMAIN.replace(':domainId', ''))
    );
  });

  //TODO: Skip this test until the vulnerability table data is loaded in localhost.
  test.skip('Test vulnerability details accessibility', async ({
    page: pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await pageAsGlobalAdmin.goto(ROUTES.VULNERABILITIES);
    await pageAsGlobalAdmin
      .getByRole('row')
      .nth(1)
      .getByRole('cell')
      .nth(7)
      .click();
    await expect(pageAsGlobalAdmin).toHaveURL(
      new RegExp(ROUTES.VULNERABILITY.replace(':vulnerabilityId', ''))
    );

    const accessibilityScanResults =
      await makeAxeBuilder(pageAsGlobalAdmin).analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });
});
