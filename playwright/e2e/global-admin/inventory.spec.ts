import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import type { TestInfo } from '@playwright/test';
import { ROUTES } from '../../../frontend/src/constants/routes';
import {
  openFiltersDrawer,
  closeFilterDrawer,
  ensureSectionOpen,
  INV
} from '../../utils/filters';

test.describe('Inventory', () => {
  test.skip('Test inventory accessibility', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await pageAsGlobalAdmin.goto(ROUTES.INVENTORY);
    const accessibilityScanResults =
      await makeAxeBuilder(pageAsGlobalAdmin).analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  test.skip('Test domain accessibility', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await pageAsGlobalAdmin.goto(ROUTES.DOMAINS);
    const accessibilityScanResults =
      await makeAxeBuilder(pageAsGlobalAdmin).analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  // TODO: Skip this test until the domain table data is loaded in localhost.
  test.skip('Test domain details accessibility', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await pageAsGlobalAdmin.goto(ROUTES.DOMAINS);
    await pageAsGlobalAdmin
      .getByRole('row')
      .nth(1)
      .getByRole('cell')
      .nth(8)
      .getByRole('button')
      .click();
    await expect(pageAsGlobalAdmin).toHaveURL(
      new RegExp(ROUTES.DOMAIN.replace(':domainId', '')),
      { timeout: 10000 }
    );

    const accessibilityScanResults =
      await makeAxeBuilder(pageAsGlobalAdmin).analyze();

    await testInfo.attach('accessibility-scan-results', {
      body: JSON.stringify(accessibilityScanResults, null, 2),
      contentType: 'application/json'
    });

    expect(accessibilityScanResults.violations).toHaveLength(0);
  });

  // TODO: Skip this test until the domain table data is loaded in localhost.
  test.skip('Test domain table filter', async ({ pageAsGlobalAdmin }) => {
    await pageAsGlobalAdmin.goto(ROUTES.DOMAINS);
    await pageAsGlobalAdmin.getByLabel('Show filters').click();
    await pageAsGlobalAdmin.getByPlaceholder('Filter value').click();
    await pageAsGlobalAdmin.getByPlaceholder('Filter value').fill('Homeland');
    await pageAsGlobalAdmin.getByPlaceholder('Filter value').press('Enter');

    let rowCount = await pageAsGlobalAdmin.getByRole('row').count();
    for (let it = 2; it < rowCount; it++) {
      await expect(
        pageAsGlobalAdmin.getByRole('row').nth(it).getByRole('cell').nth(0)
      ).toContainText('Homeland');
    }
  });

  test.describe('Filter blue dot indicators', () => {
    const filterConfigs = [
      {
        name: 'IP',
        sectionName: /^IP$/i,
        type: 'input',
        inputPlaceholder: /IP address/i,
        testValue: '192.168.1.1'
      },
      {
        name: 'Domain',
        sectionName: /^Domain$/i,
        type: 'input',
        inputPlaceholder: /Domain Name/i,
        testValue: 'example.com'
      },
      {
        name: 'Root Domains',
        sectionName: /^Root Domains$/i,
        type: 'checkbox',
        checkboxPattern: /.+/
      },
      {
        name: 'Ports',
        sectionName: /^Ports$/i,
        type: 'checkbox',
        checkboxPattern: /^(80|443|22|21|25|53|3306|8080|Unassigned)$/
      },
      {
        name: 'CVEs',
        sectionName: /^CVEs$/i,
        type: 'checkbox',
        checkboxPattern: /^CVE-/
      },
      {
        name: 'Severity',
        sectionName: /^Severity$/i,
        type: 'checkbox',
        checkboxPattern: /^(Critical|High|Medium|Low)$/i
      }
    ];

    filterConfigs.forEach((filter) => {
      test(`${filter.name} filter shows blue dot when applied`, async ({
        pageAsGlobalAdmin
      }) => {
        await pageAsGlobalAdmin.goto(ROUTES.INVENTORY);
        await openFiltersDrawer(pageAsGlobalAdmin, INV);

        await ensureSectionOpen(pageAsGlobalAdmin, filter.sectionName);

        const accordionButton = pageAsGlobalAdmin
          .getByRole('button', { name: filter.sectionName })
          .first();

        const blueDot = accordionButton.locator(
          'svg[data-testid="FiberManualRecordRoundedIcon"]'
        );

        await expect(blueDot).not.toBeVisible();

        if (filter.type === 'input') {
          const input = pageAsGlobalAdmin
            .getByPlaceholder(filter.inputPlaceholder!)
            .first();

          await expect(input).toBeVisible();
          await input.fill(filter.testValue!);
          await input.press('Enter');
          await pageAsGlobalAdmin.waitForTimeout(300);
        } else if (filter.type === 'checkbox') {
          const checkboxes = pageAsGlobalAdmin.getByRole('checkbox', {
            name: filter.checkboxPattern
          });

          const checkboxCount = await checkboxes.count();
          test.skip(
            checkboxCount === 0,
            `No ${filter.name} checkboxes available - skipping test`
          );

          await checkboxes.first().click();
          await pageAsGlobalAdmin.waitForTimeout(300);
        }

        await expect(blueDot).toBeVisible();

        const blueDotColor = await blueDot.evaluate((el) => {
          return window.getComputedStyle(el).color;
        });
        expect(blueDotColor).toBeTruthy();

        await closeFilterDrawer(pageAsGlobalAdmin, INV, { assertHidden: true });
      });
    });
  });
});
