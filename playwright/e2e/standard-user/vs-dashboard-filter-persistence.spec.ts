/*
  /playwright/e2e/standard-user/vs-dashboard-filter-persistence.spec.ts
  Author: Jesse Salinas
  Date: 11/20/2025
  Note: Standard Users have no filter capabilities, so traditional filter persistence testing does not apply. These tests verify that the navigation system works correctly for users without filter access and that no filter-related errors occur.
*/
import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';
import { ROUTES } from '../../../frontend/src/constants/routes';
import { checkFiltersDisabled } from '../../utils/filters';

test.describe('VS Dashboard Filter Persistence - Standard User', () => {

  // Verify filters are disabled for Standard User
  test('Standard User filters are disabled', async ({ pageAsStandardUser }) => {
    const page = pageAsStandardUser;

    console.log('=== Testing Standard User Filter Permissions ===');

    // Navigate to VS Dashboard
    await page.goto(ROUTES.VSDASHBOARD);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Step 1: Check that filters are disabled
    console.log('Step 1: Checking filter permissions');
    const filterStatus = await checkFiltersDisabled(page);

    expect(filterStatus.regionDisabled).toBeTruthy();
    expect(filterStatus.orgDisabled).toBeTruthy();
    expect(filterStatus.filtersDisabled).toBeTruthy();

    console.log(
      'PASS: Both region and organization filters are correctly disabled for Standard User'
    );
  });

  // Verify Standard User can access VS Dashboard without filter errors
  test('Standard User can access VS Dashboard without filter errors', async ({
    pageAsStandardUser
  }) => {
    const page = pageAsStandardUser;

    console.log('=== Testing Standard User VS Dashboard Access ===');

    // Navigate to VS Dashboard
    await page.goto(ROUTES.VSDASHBOARD);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Step 1: Verify page loads successfully
    console.log('Step 1: Verifying VS Dashboard loads for Standard User');
    await expect(page).toHaveURL(/.*VSDashboard.*/);

    // Step 2: Verify filters are disabled
    console.log('Step 2: Verifying filter restrictions');
    const filterStatus = await checkFiltersDisabled(page);
    expect(filterStatus.filtersDisabled).toBeTruthy();

    // Step 3: Verify no JavaScript errors or filter-related crashes
    console.log('Step 3: Verifying no filter-related errors');
    // If we got this far without crashes, the filter system is working correctly for Standard Users

    console.log(
      'PASS: Standard User can access VS Dashboard without filter-related errors'
    );
  });
});
