# **Playwright Testing for Crossfeed**

## **Overview**

This project uses **Playwright** for automated end-to-end testing. The Playwright testing workflow operates in two distinct modes:

1. **Local Testing via Terminal** - Running tests directly from the terminal.
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
- [GitHub Actions Testing with Amazon ECS](#github-actions-testing-with-amazon-ecs)
- [Logging into Crossfeed and Preserving Browser State](#logging-into-crossfeed-and-preserving-browser-state)
- [Adding Test Cases](#adding-test-cases)
- [Test Results](#test-results)

---

## **Prerequisites**

## Playwright configuration for Crossfeed

Since Playwright is intended to run in 2 different modes `[localhost, GitHub Actions/AWS]`, a configuration tool at `utils/env.ts` is created to help set default URLs and headless mode options.

 Environment variables pertinent to Playwright are located in `xfd/playwright/.env` and are prefixed with `PW_*`. A blank dummy file is included in the repository to satisfy linters and checkers. This file can be used to set variables for running Playwright in localhost, but do not check in that file. It is excluded by .gitignore, but be careful when checking in code.

Some environment variables values are defined in this README, but information that is secret will not be shared in this document. Ask the automated testing team for the values to continue setting up the configuration.

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
PW_XFD_URL=http://localhost
PW_XFD_USERNAME
PW_XFD_PASSWORD
PW_XFD_2FA_ISSUER
PW_XFD_2FA_SECRET
PW_XFD_USER_ROLE
PW_XFD_LOGIN
PW_HEADLESS=false
PW_CI=false
```

In local testing, `PW_HEADLESS` can optionally be set to true or false. `PW_CI` should be set to false, as this variable will adjust the behavior of how the global setup will load the other environment variables.

### **Environment Variables for Local Testing in VS Code**

If you are using testing in VS Code using the Playwright extension, add the following lines you your `settings.json`, when is accessed from `Extension Settings->Edit in settings.json`

```json
"playwright.env": {
        "PW_XFD_URL":"http://localhost",
        "PW_XFD_USERNAME":"",
        "PW_XFD_PASSWORD":"",
        "PW_XFD_2FA_ISSUER":"",
        "PW_XFD_2FA_SECRET":"",
        "PW_XFD_USER_ROLE":"",
        "PW_XFD_LOGIN" : "",
        "PW_HEADLESS" : "false",
        "PW_CI": "false"
}
```

## **GitHub Actions Testing with Amazon ECS**

In this mode, the Playwright tests are run everytime changes are committed to the develop and integration branches `xfd/frontend/` directory, or to the `xfd/.github/workflows/regression.yml` file itself. The Regression Testing workflow (which so far only encompasses Playwright) calls out to a containerized version of Crossfeed's Playwright testing suite stored on Amazon ECR via an ECS task. When the task is triggered, Playwright ECS will run against either the staging-cd or integration instances of Playwright. Test results are stored in Amazon S3 bucket and downloaded as artifacts to the GitHub Actions workflow.

There is no need for any frontend developer to alter any configuration of Playwright ECS. The entire configuration is set by the workflow process.

## **Logging into Crossfeed and Preserving Browser State**

The global setup script located at `xfd/playwright/global-setup.ts` performs the task of logging into Crossfeed and storing the browsers state to `xfd/playwright/storageState.json`. This script works by manually performing the steps to login to Crossfeed through the browser.

This process does not use the PIV card certificate process, but a username/password process with 2FA tokens. The necessary environment variables are not stored in code, but populated by the build process (manually setting environment variables, set by docker-compose, or populated by GitHub Actions).

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
