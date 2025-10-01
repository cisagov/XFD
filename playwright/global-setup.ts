// playwright/globalSetup.ts
import { chromium, FullConfig } from '@playwright/test';
import * as OTPAuth from 'otpauth';
import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';
import { determineUrl } from './utils/env';
import { userRoles } from './.auth/userRoles';

const envPath = path.resolve(__dirname, '.env');

if (!process.env.CI && fs.existsSync(envPath)) {
  console.log('📥 Running locally — loading .env file');
  dotenv.config({ path: envPath, override: true });
} else {
  console.log('🚀 Running in CI/CD — skipping .env load');
}

async function loginAndSaveStorage(
  role: string,
  username: string,
  password: string,
  totpSecret: string,
  baseUrl: string
) {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  const totp = new OTPAuth.TOTP({
    issuer: process.env.PW_XFD_2FA_ISSUER,
    label: role,
    algorithm: 'SHA1',
    digits: 6,
    period: 30,
    secret: totpSecret
  });

  console.log(`🔐 Logging in as ${role}...`);
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

  await page.getByTestId('button').click();
  await page.getByLabel('Email Address').fill(username);
  await page.getByRole('button', { name: 'Next' }).click();
  await page.waitForFunction(() => document.title.includes('Login.gov'));
  await page.getByLabel('Email address').fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.getByLabel('One-time code').fill(totp.generate());
  await page.getByRole('button', { name: 'Submit' }).click();

  // Give time for redirects/session to finalize
  await page.waitForTimeout(7000);

  const filePath = `.auth/${role}.json`;
  await page.context().storageState({ path: filePath });

  await page.close();
  await browser.close();

  console.log(`✅ Saved auth state for ${role} to ${filePath}`);
}

async function globalSetup(config: FullConfig) {
  const baseUrl = determineUrl();
  if (!baseUrl) {
    throw new Error('❌ PW_XFD_URL is not defined.');
  }

  fs.mkdirSync('.auth', { recursive: true });

  for (const { role, username, password, totpSecret } of userRoles) {
    await loginAndSaveStorage(role, username, password, totpSecret, baseUrl);
  }
}

export default globalSetup;
