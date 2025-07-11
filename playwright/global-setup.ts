import { chromium, FullConfig } from '@playwright/test';
import * as OTPAuth from 'otpauth';
import * as dotenv from 'dotenv';
import { determineUrl } from './utils/env';

dotenv.config({ path: '../.env' });

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

const waitForFrontend = async (url, timeout = 600000, checkInterval = 5000) => {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    try {
      const response = await axios.get(url);
      // Log the status code to ensure the server responds correctly
      console.log(`Frontend is ready with status code: ${response.status}`);
      return; // If the request succeeds, we know the server is up
    } catch (error) {
      // Check if the error is related to a failed HTTP request (e.g., connection refused, status code not 2xx)
      if (error.response) {
        console.log(
          `Frontend not ready yet. Status: ${error.response.status}. Retrying...`
        );
      } else {
        console.log('Error occurred while checking frontend:', error);
        break;
      }

      await new Promise((resolve) => setTimeout(resolve, checkInterval)); // Wait before retrying
    }
  }
  throw new Error(
    `Frontend did not become ready within ${timeout / 1000} seconds.`
  );
};

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
  await waitForFrontend(baseUrl);
  await page.goto(baseUrl, {
    waitUntil: 'domcontentloaded',
    timeout: 60000
  });
  await page.getByTestId('button').click();
  await page
    .getByLabel('Username (Email)')
    .fill(String(process.env.PW_XFD_LOGIN));
  await page.getByRole('button', { name: 'Next' }).click();
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
