/*
    Name: vs-dashboard-filter-persistence.spec.ts
    Author: Jesse Salinas
    Date: 2025-09-30
    Description: Test functions for VS Dashboard filter persistence during drill-down navigation (CRASM-3004)
*/

import { test, expect } from '../../axe-test';
import type { TestInfo } from '@playwright/test';

// Helper function to wait for VS Dashboard to load completely
async function waitForVSDashboardLoad(page: any) {
  // Wait for page to load initially
  await page.waitForLoadState('networkidle');
  
  // Check for and dismiss the welcome modal if it exists
  try {
    const welcomeModal = page.locator('text=Welcome to the CyHy Dashboard!');
    if (await welcomeModal.isVisible({ timeout: 3000 })) {
      console.log('Welcome modal detected, dismissing...');
      
      // Look for close button - try the most common ones first
      const dismissButtons = [
        '[aria-label="close"]',
        'button[aria-label="Close"]',
        'button:has-text("Get Started")',
        'button:has-text("Ready to dive in? Let\'s get started!")',
        '.MuiDialog-root button:last-child'
      ];
      
      for (const buttonSelector of dismissButtons) {
        try {
          const button = page.locator(buttonSelector);
          if (await button.isVisible({ timeout: 1000 })) {
            await button.click();
            console.log(`Dismissed modal using: ${buttonSelector}`);
            
            // Wait for modal to disappear
            await welcomeModal.waitFor({ state: 'hidden', timeout: 5000 });
            break;
          }
        } catch (e) {
          // Continue to next selector
        }
      }
      
      console.log('Modal dismissed, waiting for dashboard to load...');
      // Give the dashboard extra time to load after modal dismissal
      await page.waitForTimeout(2000);
    }
  } catch (e) {
    console.log('No welcome modal found or already dismissed');
  }
  
  // Wait for dashboard content to load - either data widgets OR no data message
  const dashboardContentSelectors = [
    'text=Latest Scanning Summary',
    'text=Detected Hosts', 
    'text=No matching data available',
    'text=Please select another region or organization',
    'text=There is no data on the page'
  ];
  
  let dashboardLoaded = false;
  for (const selector of dashboardContentSelectors) {
    try {
      await page.waitForSelector(selector, { timeout: 3000 });
      console.log(`Dashboard loaded - found: ${selector}`);
      dashboardLoaded = true;
      break;
    } catch (e) {
      // Continue to next selector
    }
  }
  
  if (!dashboardLoaded) {
    console.log('No dashboard content found, taking screenshot for debugging...');
    await page.screenshot({ path: 'debug-no-dashboard-content.png', fullPage: true });
  }
  
  // Wait for filter components to be ready - but make it optional since they might not exist
  try {
    await page.waitForSelector('label:has-text("Region")', { timeout: 10000 });
    console.log('Region filter found');
  } catch (e) {
    console.log('Region filter not found - this page might not have filters');
    // Don't throw error, just continue
  }
}

// Helper function to get current filter values
async function getCurrentFilters(page: any) {
  // Look for input fields by their labels
  const regionFilter = await page.$('label:has-text("Region") + div input, label:has-text("Region") ~ div input');
  const orgFilter = await page.$('label:has-text("Organization") + div input, label:has-text("Organization") ~ div input');
  
  const regionValue = regionFilter ? await regionFilter.inputValue() : null;
  const orgValue = orgFilter ? await orgFilter.inputValue() : null;
  
  return { region: regionValue, organization: orgValue };
}

// Helper function to set filters
async function setFilters(page: any, region: string | null, organization: string | null) {
  if (region) {
    // Click on the region autocomplete field
    await page.click('label:has-text("Region") + div, label:has-text("Region") ~ div');
    await page.waitForSelector(`text=${region}`, { timeout: 5000 });
    await page.click(`text=${region}`);
    await page.waitForLoadState('networkidle');
  }
  
  if (organization) {
    // Click on the organization autocomplete field
    await page.click('label:has-text("Organization") + div, label:has-text("Organization") ~ div');
    await page.waitForSelector(`text=${organization}`, { timeout: 5000 });
    await page.click(`text=${organization}`);
    await page.waitForLoadState('networkidle');
  }
}

test.describe('VS Dashboard Filter Persistence', () => {
  test('should preserve filters when drilling down to vulnerability details and returning', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    // Navigate to VS Dashboard
    await page.goto('/VSDashboard');
    await waitForVSDashboardLoad(page);

    // Set specific region and organization filters
    await setFilters(page, 'Region 2', null); // Set region but leave org empty for this test
    
    // Get the current filter state before drill-down
    const filtersBeforeDrillDown = await getCurrentFilters(page);
    console.log('Filters before drill-down:', filtersBeforeDrillDown);

    // Find and click on a vulnerability to drill down
    // Look for any clickable links that might lead to vulnerability details
    // This could be in various widgets - let's try common patterns
    const vulnerabilityLink = page.locator('a[href*="/vulnerabilities"], a[href*="/vulnerability"], button:has-text("View"), a:has-text("CVE-")').first();
    await expect(vulnerabilityLink).toBeVisible({ timeout: 10000 });
    await vulnerabilityLink.click();

    // Wait for navigation to vulnerability details page
    await page.waitForURL(/.*\/vulnerabilities\/.*/, { timeout: 10000 });
    await page.waitForLoadState('networkidle');

    // Navigate back to VS Dashboard
    await page.goBack();
    await waitForVSDashboardLoad(page);

    // Get filter state after returning
    const filtersAfterReturn = await getCurrentFilters(page);
    console.log('Filters after return:', filtersAfterReturn);

    // Verify filters are preserved
    expect(filtersAfterReturn.region).toBe(filtersBeforeDrillDown.region);
    expect(filtersAfterReturn.organization).toBe(filtersBeforeDrillDown.organization);

    // Verify the data is still filtered correctly
    // Check that dashboard widgets are visible and showing data
    const dashboardWidget = page.locator('text=Latest Scanning Summary, text=Key Metrics, text=Top Vulnerabilities').first();
    await expect(dashboardWidget).toBeVisible();

    // Accessibility scan
    const results = await makeAxeBuilder()
      .analyze(); // Scan the entire page since we don't have a specific container
    await testInfo.attach('accessibility-scan-results-filter-persistence', {
      body: JSON.stringify(results, null, 2),
      contentType: 'application/json'
    });

    expect(results.violations).toHaveLength(0);
  });

  test('should reset to user default region on page reload', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    // Navigate to VS Dashboard
    await page.goto('/VSDashboard');
    await waitForVSDashboardLoad(page);

    // Set filters to non-default values
    await setFilters(page, 'Region 9', null);
    
    // Get current filters
    const filtersBeforeReload = await getCurrentFilters(page);
    console.log('Filters before reload:', filtersBeforeReload);

    // Reload the page
    await page.reload();
    await waitForVSDashboardLoad(page);

    // Get filters after reload
    const filtersAfterReload = await getCurrentFilters(page);
    console.log('Filters after reload:', filtersAfterReload);

    // Verify region resets to user's default (assuming user's default is Region 1)
    // This test assumes the test user's default region is "1"
    expect(filtersAfterReload.region).toContain('Region 1');
    
    // Verify organization is empty/undefined after reload
    expect(filtersAfterReload.organization).toBeFalsy();

    // Accessibility scan
    const results = await makeAxeBuilder()
      .analyze();
    await testInfo.attach('accessibility-scan-results-page-reload', {
      body: JSON.stringify(results, null, 2),
      contentType: 'application/json'
    });

    expect(results.violations).toHaveLength(0);
  });

  test('should preserve "All Regions" filter during drill-down', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    // Navigate to VS Dashboard
    await page.goto('/VSDashboard');
    await waitForVSDashboardLoad(page);

    // Set "All Regions" filter
    await setFilters(page, 'All Regions', null);
    
    const filtersBeforeDrillDown = await getCurrentFilters(page);
    console.log('All Regions filter before drill-down:', filtersBeforeDrillDown);

    // Drill down to vulnerability details
    const vulnerabilityLink = page.locator('[data-testid="vulnerability-link"]').first();
    await expect(vulnerabilityLink).toBeVisible({ timeout: 10000 });
    await vulnerabilityLink.click();

    // Wait for navigation and return
    await page.waitForURL(/.*\/vulnerabilities\/.*/, { timeout: 10000 });
    await page.goBack();
    await waitForVSDashboardLoad(page);

    // Verify "All Regions" is still selected
    const filtersAfterReturn = await getCurrentFilters(page);
    console.log('All Regions filter after return:', filtersAfterReturn);
    
    expect(filtersAfterReturn.region).toContain('All Regions');

    // Accessibility scan
    const results = await makeAxeBuilder()
      .analyze();
    await testInfo.attach('accessibility-scan-results-all-regions', {
      body: JSON.stringify(results, null, 2),
      contentType: 'application/json'
    });

    expect(results.violations).toHaveLength(0);
  });

  test('should clear organization filter when region changes', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    // Navigate to VS Dashboard
    await page.goto('/VSDashboard');
    await waitForVSDashboardLoad(page);

    // Set both region and organization
    await setFilters(page, 'Region 2', null);
    
    // Wait for organization options to populate based on region
    await page.waitForTimeout(1000);
    
    // Select an organization (assuming there's at least one available)
    await page.click('label:has-text("Organization") + div, label:has-text("Organization") ~ div');
    
    // Wait for org options and select the first available one
    // Organization options appear in a dropdown/listbox
    await page.waitForSelector('li[role="option"], .MuiAutocomplete-option', { timeout: 5000 });
    const firstOrgOption = page.locator('li[role="option"], .MuiAutocomplete-option').first();
    await firstOrgOption.click();
    await page.waitForLoadState('networkidle');

    // Get filters with both region and org set
    const filtersWithBoth = await getCurrentFilters(page);
    console.log('Filters with both region and org:', filtersWithBoth);

    // Change region - this should clear the organization
    await setFilters(page, 'Region 3', null);

    // Verify organization is cleared
    const filtersAfterRegionChange = await getCurrentFilters(page);
    console.log('Filters after region change:', filtersAfterRegionChange);
    
    expect(filtersAfterRegionChange.region).toContain('Region 3');
    expect(filtersAfterRegionChange.organization).toBeFalsy();

    // Accessibility scan
    const results = await makeAxeBuilder()
      .analyze();
    await testInfo.attach('accessibility-scan-results-cascade-clear', {
      body: JSON.stringify(results, null, 2),
      contentType: 'application/json'
    });

    expect(results.violations).toHaveLength(0);
  });

  test('should maintain filter state when navigating between filter-enabled pages', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    // Navigate to VS Dashboard and set filters
    await page.goto('/VSDashboard');
    await waitForVSDashboardLoad(page);
    await setFilters(page, 'Region 2', null);
    
    const filtersOnVSDashboard = await getCurrentFilters(page);
    console.log('Filters on VS Dashboard:', filtersOnVSDashboard);

    // Navigate to inventory page (another filter-enabled page)
    await page.goto('/inventory');
    await page.waitForLoadState('networkidle');

    // Navigate back to VS Dashboard
    await page.goto('/VSDashboard');
    await waitForVSDashboardLoad(page);

    // Verify filters are restored
    const filtersAfterNavigation = await getCurrentFilters(page);
    console.log('Filters after navigation:', filtersAfterNavigation);
    
    expect(filtersAfterNavigation.region).toBe(filtersOnVSDashboard.region);

    // Accessibility scan
    const results = await makeAxeBuilder()
      .analyze();
    await testInfo.attach('accessibility-scan-results-cross-page', {
      body: JSON.stringify(results, null, 2),
      contentType: 'application/json'
    });

    expect(results.violations).toHaveLength(0);
  });

  test('should not show region flickering on page load', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    // Navigate to VS Dashboard
    await page.goto('/VSDashboard');

    // Wait a short moment for initial load
    await page.waitForTimeout(100);

    // Get the initial region value quickly after load
    const initialRegion = await getCurrentFilters(page);
    console.log('Initial region value:', initialRegion.region);

    // Wait for full dashboard load
    await waitForVSDashboardLoad(page);

    // Get the final region value after full load
    const finalRegion = await getCurrentFilters(page);
    console.log('Final region value:', finalRegion.region);

    // Verify the region value didn't change during load (no flickering)
    // Both should be the same, indicating no 1→9→1 flickering occurred
    expect(initialRegion.region).toBeTruthy(); // Should have a value
    expect(finalRegion.region).toBe(initialRegion.region); // Should be the same value

    // Accessibility scan
    const results = await makeAxeBuilder()
      .analyze();
    await testInfo.attach('accessibility-scan-results-no-flicker', {
      body: JSON.stringify(results, null, 2),
      contentType: 'application/json'
    });

    expect(results.violations).toHaveLength(0);
  });
});
