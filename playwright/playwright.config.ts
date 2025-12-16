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

const IS_CI =
  (process.env.CI ?? '').toLocaleLowerCase() === 'true' ||
  process.env.CI === '1';

const reporters: any[] = IS_CI
  ? [['dot'], ['github']]
  : [
      ['list', { printSteps: true }],
      ['json', { outputFile: 'playwright-report/results.json' }],
      ['html', { outputFolder: 'playwright-report/html', open: 'never' }]
    ];

export default defineConfig({
  globalSetup: './global-setup',
  testDir: './e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: IS_CI,
  /* Retry on CI only */
  retries: 3,
  /* Opt out of parallel tests on CI. */
  workers: 2,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: reporters,
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.PW_XFD_URL,
    headless: IS_CI,

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
