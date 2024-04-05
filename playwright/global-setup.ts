import { chromium, FullConfig, test as setup } from '@playwright/test';
import * as OTPAuth from 'otpauth';
import * as dotenv from 'dotenv';

dotenv.config();

const authFile = './storageState.json';

let totp = new OTPAuth.TOTP({
  issuer: process.env.PW_XFD_2FA_ISSUER,
  label: 'Crossfeed',
  algorithm: 'SHA1',
  digits: 6,
  period: 30,
  secret: process.env.PW_XFD_2FA_SECRET
});

async function globalSetup(config: FullConfig) {
  const { baseURL, storageState } = config.projects[0].use;
  const browser = await chromium.launch();
  const page = await browser.newPage();

  //Log in with credentials.
  await page.goto(String(process.env.PW_XFD_URL));
  await page
    .getByPlaceholder('Enter your email address')
    .fill(String(process.env.PW_XFD_USERNAME));
  await page
    .getByPlaceholder('Enter your password')
    .fill(String(process.env.PW_XFD_PASSWORD));
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page
    .getByPlaceholder('Enter code from your authenticator app')
    .fill(totp.generate());
  await page.getByRole('button', { name: 'Confirm' }).click();
  //Wait for storageState to write to json file for other tests to use.
  await page.waitForTimeout(1000);
  await page.context().storageState({ path: authFile });
  await page.close();
}

export default globalSetup;
