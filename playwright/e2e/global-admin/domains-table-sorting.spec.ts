/*
    Name: domains-table-sorting.spec.ts
    Author: Jesse Salinas
    Date: 2024-09-16
    Description: Test functions for server-side table sorting
*/

import { test, expect } from '../../axe-test';
import type { TestInfo } from '@playwright/test';

// Helper function to validate IP address natural sorting order
function validateIpSorting(ipAddresses: string[]): boolean {
  if (ipAddresses.length <= 1) return true;

  for (let i = 0; i < ipAddresses.length - 1; i++) {
    const current = ipAddresses[i];
    const next = ipAddresses[i + 1];

    // Convert IP addresses to comparable numeric format
    const currentParts = current.split('.').map((part) => parseInt(part, 10));
    const nextParts = next.split('.').map((part) => parseInt(part, 10));

    // Compare each octet
    for (let j = 0; j < 4; j++) {
      if (currentParts[j] < nextParts[j]) {
        break; // Current is less than next, order is correct
      } else if (currentParts[j] > nextParts[j]) {
        return false; // Current is greater than next, order is incorrect
      }
      // If equal, continue to next octet
    }
  }
  return true;
}

// Helper function to validate domain natural sorting order
function validateDomainSorting(domains: string[]): boolean {
  if (domains.length <= 1) return true;

  for (let i = 0; i < domains.length - 1; i++) {
    const current = domains[i].toLowerCase();
    const next = domains[i + 1].toLowerCase();

    if (current > next) {
      return false; // Current is greater than next, order is incorrect
    }
  }
  return true;
}

test.describe('domains-table', () => {
  test('IP column sorts with server-side sorting', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await page.goto('/inventory/domains');
    await page.waitForSelector('[aria-label="Domains Table"]');

    // Click IP column header to sor
    await page.getByRole('columnheader', { name: /IP/i }).click();

    // Wait for the table to update after server-side sor
    await page.waitForLoadState('networkidle');

    // Get sorted IP values using the correct selector
    const sortedIpCells = await page
      .getByRole('gridcell', { name: /IP Address for Domain/ })
      .allTextContents();

    // Accessibility scan scoped to the domains table only
    const results = await makeAxeBuilder()
      .include('[aria-label="Domains Table"]')
      .analyze();
    await testInfo.attach('accessibility-scan-results-ip', {
      body: JSON.stringify(results, null, 2),
      contentType: 'application/json'
    });

    // Verify that sorting actually occurred
    expect(sortedIpCells).toBeDefined();
    expect(sortedIpCells.length).toBeGreaterThan(0);

    // Validate that IPs are in natural sorted order (ascending)
    const isIpSortingValid = validateIpSorting(sortedIpCells);
    expect(isIpSortingValid).toBe(true);

    // Log the sorted IPs for debugging
    console.log('Sorted IP addresses:', sortedIpCells);

    expect(results.violations).toHaveLength(0);
  });

  test('Domain column sorts with server-side sorting', async ({
    page,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await page.goto('/inventory/domains');
    await page.waitForSelector('[aria-label="Domains Table"]');

    // Click Domain column header to sor
    await page.getByRole('columnheader', { name: /Domain/i }).click();

    // Wait for the table to update after server-side sor
    await page.waitForLoadState('networkidle');

    // Get sorted domain values using the correct selector
    const sortedDomainCells = await page
      .getByRole('gridcell', { name: /Domain Name:/ })
      .allTextContents();

    // Accessibility scan scoped to the domains table only
    const results = await makeAxeBuilder()
      .include('[aria-label="Domains Table"]')
      .analyze();
    await testInfo.attach('accessibility-scan-results-domain', {
      body: JSON.stringify(results, null, 2),
      contentType: 'application/json'
    });

    // Verify that sorting actually occurred
    expect(sortedDomainCells).toBeDefined();
    expect(sortedDomainCells.length).toBeGreaterThan(0);

    // Validate that domains are in natural sorted order (ascending)
    const isDomainSortingValid = validateDomainSorting(sortedDomainCells);
    expect(isDomainSortingValid).toBe(true);

    // Log the sorted domains for debugging
    console.log('Sorted domain names:', sortedDomainCells);

    expect(results.violations).toHaveLength(0);
  });
});
