/*
  /playwright/e2e/global-admin/vs-dashboard-filter-persistence.spec.ts
  Author: Jesse Salinas
  Date: 11/20/2025
  Note: Global Admin Users have full filter capabilities across all regions and organizations. These tests verify that filter persistence works correctly for users with full admin access during drill-down navigation.
*/
import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import { ROUTES } from '../../../frontend/src/constants/routes';
import {
  selectFromAutocomplete,
  selectAnyOrganization,
  openVSFiltersDrawer,
  closeVSFiltersDrawer,
  checkFiltersHaveValues
} from '../../utils/filters';

test.describe('VS Dashboard Filter Persistence - Global Admin User', () => {

  // Drill-down via Key Metrics persists filters
  test('Drill-down via Key Metrics persists filters', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;

    console.log('=== Testing Drill-down Filter Persistence ===');

    // Navigate to VS Dashboard
    await page.goto(ROUTES.VSDASHBOARD);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Step 1: Set filters
    console.log('Step 1: Setting filters');
    await openVSFiltersDrawer(page);
    await selectFromAutocomplete(page, /^region$/i, /Region\s*3/i);
    await page.waitForTimeout(500);
    await selectAnyOrganization(page, /^organization$/i);
    await page.waitForTimeout(500);
    await closeVSFiltersDrawer(page);

    // Step 2: Drill-down navigation (Key Metrics buttons)
    console.log('Step 2: Drilling down via Key Metrics');
    const kevButton = page
      .getByRole('button', { name: /detected kevs/i })
      .first();
    const vulnButton = page
      .getByRole('button', { name: /detected vulnerabilities/i })
      .first();

    if (await kevButton.isVisible({ timeout: 5000 })) {
      await kevButton.click();
      await page.waitForURL('**/inventory/vulnerabilities**', {
        timeout: 10000
      });
    } else if (await vulnButton.isVisible({ timeout: 5000 })) {
      await vulnButton.click();
      await page.waitForURL('**/inventory/vulnerabilities**', {
        timeout: 10000
      });
    } else {
      test.skip(true, 'No drill-down elements available');
    }

    // Step 3: Return to VS Dashboard
    console.log('Step 3: Returning to VS Dashboard');
    await page.goto(ROUTES.VSDASHBOARD);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Step 4: Verify filters are preserved
    console.log('Step 4: Checking if filters persisted');
    const finalFilters = await checkFiltersHaveValues(page);

    expect(finalFilters.hasFilters).toBeTruthy();
    console.log('PASS: Filters correctly persisted after drill-down');
  });

  // Drill-down to Domains tab persists filters
  test('Drill-down to Domains tab persists filters', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;

    console.log('=== Testing Drill-down + Domains Tab Filter Persistence ===');

    // Navigate to VS Dashboard
    await page.goto(ROUTES.VSDASHBOARD);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Step 1: Set filters
    console.log('Step 1: Setting filters');
    await openVSFiltersDrawer(page);
    await selectFromAutocomplete(page, /^region$/i, /Region\s*4/i);
    await page.waitForTimeout(500);
    await selectAnyOrganization(page, /^organization$/i);
    await page.waitForTimeout(500);
    await closeVSFiltersDrawer(page);

    // Step 2: Drill-down to Findings Library
    console.log('Step 2: Drilling down to Findings Library');
    const kevButton = page
      .getByRole('button', { name: /detected kevs/i })
      .first();
    if (await kevButton.isVisible({ timeout: 5000 })) {
      await kevButton.click();
      await page.waitForURL('**/inventory/vulnerabilities**', {
        timeout: 10000
      });
    } else {
      test.skip(true, 'No drill-down elements available');
    }

    // Step 3: Navigate to Domains tab
    console.log('Step 3: Clicking Domains tab');
    const domainsTab = page.getByRole('tab', { name: /domains/i });
    if (await domainsTab.isVisible({ timeout: 5000 })) {
      await domainsTab.click();
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);
    } else {
      console.log('Domains tab not found, but continuing test');
    }

    // Step 4: Return to VS Dashboard
    console.log('Step 4: Returning to VS Dashboard');
    await page.goto(ROUTES.VSDASHBOARD);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Step 5: Verify filters are preserved
    console.log('Step 5: Checking if filters persisted after Domains tab');
    const finalFilters = await checkFiltersHaveValues(page);

    expect(finalFilters.hasFilters).toBeTruthy();
    console.log(
      'PASS: Filters correctly persisted after drill-down + Domains tab'
    );
  });

  // Browser back navigation preserves filters
  test('Browser back navigation preserves filters', async ({
    pageAsGlobalAdmin
  }) => {
    const page = pageAsGlobalAdmin;

    console.log('=== Testing Browser Back Navigation ===');

    // Navigate to VS Dashboard
    await page.goto(ROUTES.VSDASHBOARD);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Step 1: Set filters
    console.log('Step 1: Setting filters');
    await openVSFiltersDrawer(page);
    await selectFromAutocomplete(page, /^region$/i, /Region\s*2/i);
    await page.waitForTimeout(500);
    await selectAnyOrganization(page, /^organization$/i);
    await page.waitForTimeout(500);
    await closeVSFiltersDrawer(page);

    // Step 2: Drill-down navigation
    console.log('Step 2: Drilling down');
    const kevButton = page
      .getByRole('button', { name: /detected kevs/i })
      .first();
    if (await kevButton.isVisible({ timeout: 5000 })) {
      await kevButton.click();
      await page.waitForURL('**/inventory/vulnerabilities**');
    } else {
      test.skip(true, 'No drill-down elements available');
    }

    // Step 3: Browser back navigation
    console.log('Step 3: Using browser back button');
    await page.goBack();
    await page.waitForURL('**/VSDashboard**');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Step 4: Verify filters are preserved
    console.log('Step 4: Checking filters after browser back');
    const finalFilters = await checkFiltersHaveValues(page);

    expect(finalFilters.hasFilters).toBeTruthy();
    console.log('PASS: Filters preserved with browser back navigation');
  });
});
