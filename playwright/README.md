# **Playwright Testing for Crossfeed**

## **Overview**

This project uses **Playwright** for automated end-to-end testing. The Playwright testing workflow operates in three distinct modes:

1. **Local Testing via Terminal** - Running tests directly from the terminal.
2. **Local Testing via Docker** - Running tests within a Docker container locally.
3. **AWS Regression Workflow** - Running tests on AWS ECS and uploading results to an S3 bucket.

This README will guide you through setting up, configuring, and running Playwright tests in each mode, as well as handling the deployment process for AWS.

---

## **Table of Contents**

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Playwright Configuration for Crossfeed](#playwright-configuration-for-crossfeed)
- [Local Testing via Terminal](#local-testing-via-terminal)
  - [Environment Variables for Local Testing](#environment-variables-for-local-testing)
  - [Environment Variables for Local Testing in VS Code](#environment-variables-for-local-testing-in-vs-code)
- [Local Testing via Docker](#local-testing-via-docker)
- [Logging into Crossfeed and Preserving Browser State](#logging-into-crossfeed-and-preserving-browser-state)
- [Adding Test Cases](#adding-test-cases)
- [Test Results](#test-results)

---

## **Prerequisites**

## Playwright configuration for Crossfeed

Since Playwright is intended to run in 3 different modes `[localhost, local Docker, Github Actions/AWS]`, a configuration tool at `utils/env.ts` is created to help set default URLs and headless mode options.

The `PW_XFD_URL` environment variable is to be set by the build processes. If no variable has been set, by default it will try to test against `http://localhost` . The pertinent environment variables are located in `xfd/.env` and are prefixed with `PW_*`

## **Local Testing via Terminal**

This mode is intended for frontend developers to write their own feature test cases during development. To run Playwright tests locally from the terminal:

1. Install Playwright and its dependencies by following the official [Playwright installation guide](https://playwright.dev/docs/intro#installing-playwright).

2. Run Playwright Tests from the `xfd/playwright` folder

    ```bash
    npx playwright test
    ```

    Tests are defined in the `e2e/global-admin` folder and denoted by a `.spec.ts` file extension.

3. Test Results are written to `playwright-report/results.json` for JSON data, and `playwright-report/html` for HTML reports.

### **Environment Variables for Local Testing**

For local testing, the following variables need to be loaded into your environment.

```env
PW_XFD_USERNAME
PW_XFD_PASSWORD
PW_XFD_2FA_ISSUER
PW_XFD_2FA_SECRET
PW_XFD_USER_ROLE
PW_XFD_LOGIN
```

### **Environment Variables for Local Testing in VS Code**

If you are using testing in VS Code using the Playwright extension, add the following lines you your `settings.json`, when is accessed from `Extension Settings->Edit in settings.json`

```json
"playwright.env": {
        "PW_XFD_URL":"",
        "PW_XFD_USERNAME":"",
        "PW_XFD_PASSWORD":"",
        "PW_XFD_2FA_ISSUER":"",
        "PW_XFD_2FA_SECRET":"",
        "PW_XFD_USER_ROLE":"",
        "PW_XFD_LOGIN" : ""
}
```

## **Local Testing via Docker**

This mode is intended to kick off as part of the build process. A docker container will be created using the same Playwright test.

A wait feature will listen for the frontend to begin accepting requests, as the frontend will take longer to compile than Playwright to be ready for testing. When a code 200 is received from the frontend, the Playwright tests will begin.

## **Logging into Crossfeed and Preserving Browser State**

The global setup script located at `xfd/playwright/global-setup.ts` performs the task of logging into Crossfeed and storing the browsers state to `xfd/playwright/storageState.json`. This script works by manually performing the steps to login to Crossfeed through the browser.

This process does not use the PIV card certificate process, but a username/password process with 2FA tokens. The necessary environment variables are not stored in code, but populated by the build process (manually setting environment variables, set by docker-compose, or populated by Github Actions).

The login process also uses `waitForFrontend()` to listen for a response code 200 from Crossfeed's frontend before performing the login procedure.

The `OTPAuth` module is used to generate the 2FA token needed for login, using a 2FA secret string that is not released publically.

If the global setup script fails to login, manually check the login process by logging in with the service account username/password and 2FA combo. If the Okta login process is slightly different than from what the script is anticipating, it will fail. Sometimes logging in can resolve some extra menus or checkboxes that may occassionally pop up. Unfortunately since we don't own the process, our ability to login in an automated manner is somewhat fragile.

## **Adding Test Cases**

Test cases are added by adding `*.spec.ts` files under the `xfd/playwright/e2e` folder.

Tests are defined with a `.beforeEach()` and `.afterEach()` method which create a new browser instance for each individual test case. Each test case is its own discrete task, and the success or failure state of one case should not affect the status of other cases (unless otherwise intended).

```typescript
test.describe('home', () => {
  test.beforeEach(async ({ browser }) => {
    const context = await browser.newContext();
    page = await context.newPage();
    await page.goto('/');
  });

  test.afterEach(async () => {
    await page.close();
  });
  ```

## **Test Results**

  Test results are written out to `xfd/playwright/playwright-report`. The most recent run is written out to `html/index.html` for the HTML version, and `results.json` for the latest JSON test report data.
