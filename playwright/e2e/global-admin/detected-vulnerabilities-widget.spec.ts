import { test, expect } from '@playwright/test';

test.describe('Known Exploited and Other Detected Vulnerabilities Widget', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard page before each test
    await page.goto('/VSDashboard');
  });

  test('should display main widget heading and tooltip', async ({ page }) => {
    // Check that the main widget heading is visible
    const heading = page.getByRole('heading', {
      name: /known exploited and other detected vulnerabilities/i
    });
    await expect(heading).toBeVisible();

    // Click on the info tooltip and verify icon is visible
    const tooltipButton = page.getByRole('button', {
      name: /more information about known exploited and other detected vulnerabilities/i
    });
    await tooltipButton.click();
  });

  test('should navigate to details page when clicking "View Details"', async ({
    page
  }) => {
    // Verify "View Details" link is visible and navigates correctly
    const detailsLink = page
      .getByRole('link', { name: /view details/i })
      .nth(0);
    await expect(detailsLink).toBeVisible();
    await detailsLink.click();
    await expect(page).toHaveURL(/\/inventory\/vulnerabilities$/);
  });

  //========= Severity by Prominenece ==========

  test('should toggle severity by prominence graph data using KEV, Distinct, All buttons', async ({
    page
  }) => {
    // Scope radios to the "Severity by Prominence" section
    const heading = page.getByRole('heading', {
      name: /severity by prominence/i
    });
    const group = heading.locator(
      'xpath=following::div[@role="radiogroup"][1]'
    );

    const kevBtn = group.getByRole('radio', { name: 'KEV' });
    const distinctBtn = group.getByRole('radio', { name: 'Distinct' });
    const allBtn = group.getByRole('radio', { name: 'All' });

    await kevBtn.isVisible();
    await expect(kevBtn).toHaveAttribute('aria-checked', 'true');

    await distinctBtn.click();
    await expect(distinctBtn).toHaveAttribute('aria-checked', 'true');

    await allBtn.click();
    await expect(allBtn).toHaveAttribute('aria-checked', 'true');
  });

  test('should render severity bars with correct labels', async ({ page }) => {
    // Locate all bars on the graph with aria-labels
    const bars = page.locator('[role="button"][aria-label^="Bar"]');
    //await expect(bars).toHaveCount(4); // Critical, High, Medium, Low

    // Validate each bar's aria-label
    await expect(bars.nth(0)).toHaveAttribute('aria-label', /critical/i);
    await expect(bars.nth(1)).toHaveAttribute('aria-label', /high/i);
    await expect(bars.nth(2)).toHaveAttribute('aria-label', /medium/i);
    await expect(bars.nth(3)).toHaveAttribute('aria-label', /low/i);
  });

  test(' severity chart bar colors are correct for KEV, Distinct, and All', async ({
    page
  }) => {
    const bars = page.locator('svg .MuiBarElement-root');
    //await expect(bars).toHaveCount(4);

    // KEV
    await page.getByRole('radio', { name: 'KEV' }).first();
    const kevFill = await bars.nth(0).getAttribute('fill');
    expect(kevFill).toBe('#002B45');

    // Distinct
    await page.getByRole('radio', { name: 'Distinct' }).first().click();
    const distinctFill = await bars.nth(0).getAttribute('fill');
    expect(distinctFill).toBe('#005288');

    // All
    await page.getByRole('radio', { name: 'All' }).first().click();
    const allFill = await bars.nth(0).getAttribute('fill');
    expect(allFill).toBe('#0078AE');
  });

  // ====== Top Vulnerability by Occurrence =======

  test('should toggle  occurrence table data using KEV and All buttons', async ({
    page
  }) => {
    // Scope radios to the "Top Vulnerabilities by Occurrence" section
    const heading = page.getByRole('heading', {
      name: /top vulnerabilities by occurrence/i
    });
    const group = heading.locator(
      'xpath=following::div[@role="radiogroup"][1]'
    );

    const kevBtn = group.getByRole('radio', { name: 'KEV' });
    const allBtn = group.getByRole('radio', { name: 'All' });

    await kevBtn.isVisible();
    await expect(kevBtn).toHaveAttribute('aria-checked', 'true');

    await allBtn.click();
    await expect(allBtn).toHaveAttribute('aria-checked', 'true');
  });

  test('should display vulnerability occurrunce table with correct columns and data', async ({
    page
  }) => {
    // Assert the table headers are visible
    const table = page.locator('table');
    await expect(
      table.getByRole('columnheader', { name: 'Vulnerability Name' })
    ).toBeVisible();
    await expect(
      table.getByRole('columnheader', { name: 'Host Counts' })
    ).toBeVisible();
    await expect(
      table.getByRole('columnheader', { name: 'Severity' })
    ).toBeVisible();
    await expect(
      table.getByRole('columnheader', { name: 'CVSS Score' })
    ).toBeVisible();

    // Check that first row has a clickable CVE link
    const firstCell = page
      .getByRole('cell', { name: /Vulnerability Name CVE-\d{4}-\d+/ })
      .first();
    await expect(firstCell).toBeVisible();
    await firstCell.click();
  });

  test('hover tooltips show text for all info icons', async ({ page }) => {
    // Small helper to reduce flakiness with MUI’s show/leave delays
    const resetHover = async () => {
      await page.mouse.move(0, 0);
      await page.waitForTimeout(80); // give Popper time to close the prior tooltip
    };

    // 1) Main widget info icon
    await resetHover();
    const mainInfo = page.getByRole('button', {
      name: /more information about known exploited and other detected vulnerabilities/i
    });
    const mainTooltip = page
      .getByRole('tooltip')
      .filter({ hasText: /known exploited and other/i }); // use a stable substring
    await mainInfo.hover();
    await expect(mainTooltip).toBeVisible();
    await expect(mainTooltip).not.toHaveText('');

    // 2) Severity by Prominence info icon
    await resetHover();
    const sevInfo = page.getByRole('button', {
      name: /more information about severity by prominence/i
    });
    const sevTooltip = page
      .getByRole('tooltip')
      .filter({ hasText: /severity by prominence/i });
    await sevInfo.hover();
    await expect(sevTooltip).toBeVisible();
    await expect(sevTooltip).not.toHaveText('');

    // 3) Top Vulnerabilities by Occurrence info icon
    await resetHover();
    const topInfo = page.getByRole('button', {
      name: /more information about top vulnerabilities by occurrence/i
    });
    const topTooltip = page
      .getByRole('tooltip')
      .filter({ hasText: /top vulnerabilities by occurrence/i });
    await topInfo.hover();
    await expect(topTooltip).toBeVisible();
    await expect(topTooltip).not.toHaveText('');
  });
});
