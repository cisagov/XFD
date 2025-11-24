import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// require('dotenv').config();

/**
 * See https://playwright.dev/docs/test-configuration.
 */

dotenv.config();

const reporters: any[] = process.env.CI
  ? [
      ['list', { printSteps: true }],
      ['github'] // only enabled in CI/CD
    ]
  : [
      ['json', { outputFile: 'playwright-report/results.json' }],
      ['html', { outputFolder: 'playwright-report/html', open: 'never' }]
    ];

export default defineConfig({
  globalSetup: './global-setup',
  testDir: './e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 2 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: reporters,
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.PW_XFD_URL,
    headless: !!process.env.CI || false,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry'
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'ui-regression',
      testMatch: ['**/*.spec.ts'],
      testIgnore: ['**/*.axe.spec.ts'],
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'accessibility',
      testMatch: ['**/*.axe.spec.ts'],
      use: { ...devices['Desktop Chrome'] }
    }
  ]
});
