import { chromium, FullConfig } from '@playwright/test';
import * as OTPAuth from 'otpauth';
import * as dotenv from 'dotenv';
import { determineUrl } from './utils/env';
import * as fs from 'fs';
import * as path from 'path';

const envPath = path.resolve(__dirname, '.env');
const isCI = process.env.PW_CI === 'true';

if (!isCI && fs.existsSync(envPath)) {
  console.log('📥 Running locally — loading .env file');
  dotenv.config({ path: envPath, override: true });
} else {
  console.log('🚀 Running in CI/CD — skipping .env load');
}

const authFile = './storageState.json';

let totp = new OTPAuth.TOTP({
  issuer: process.env.PW_XFD_2FA_ISSUER,
  label: 'Crossfeed',
  algorithm: 'SHA1',
  digits: 6,
  period: 30,
  secret: process.env.PW_XFD_2FA_SECRET
});

const axios = require('axios');

async function globalSetup(config: FullConfig) {
  const baseUrl = determineUrl();
  console.log(`Base URL: ${baseUrl}`);
  if (!baseUrl) {
    throw new Error(
      '❌ PW_XFD_URL is not defined. Make sure it is set as an environment variable.'
    );
  }
  const browser = await chromium.launch();
  const page = await browser.newPage();

  //Log in with credentials.
  await page.goto(baseUrl, {
    waitUntil: 'domcontentloaded',
    timeout: 60000
  });
  await page.getByTestId('button').click();
  await page.getByLabel('Email Address').fill(String(process.env.PW_XFD_LOGIN));

  await page.getByRole('button', { name: 'Next' }).click();
  await page.waitForFunction(() => document.title.includes('Login.gov'));
  await page
    .getByLabel('Email address')
    .fill(String(process.env.PW_XFD_USERNAME));
  await page
    .getByLabel('Password', { exact: true })
    .fill(String(process.env.PW_XFD_PASSWORD));
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.getByLabel('One-time code').fill(totp.generate());
  await page.getByRole('button', { name: 'Submit' }).click();
  //Wait for storageState to write to json file for other tests to use.
  await page.waitForTimeout(7000);
  await page.context().storageState({ path: authFile });
  await page.close();
}

export default globalSetup;
