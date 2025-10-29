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

 Environment variables pertinent to Playwright are located in `xfd/playwright/.env` and are prefixed with `PW_*`. Some environment variables values are defined in this README, but information that is secret will not be shared in this document. Ask the automated testing team for the values to continue setting up the configuration.

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
PW_GLOBAL_ADMIN_USERNAME=
PW_GLOBAL_ADMIN_PASSWORD=
PW_GLOBAL_ADMIN_2FA_SECRET=

PW_REGIONAL_ADMIN_USERNAME=
PW_REGIONAL_ADMIN_PASSWORD=
PW_REGIONAL_ADMIN_2FA_SECRET=

PW_GLOBAL_VIEW_USERNAME=
PW_GLOBAL_VIEW_PASSWORD=
PW_GLOBAL_VIEW_2FA_SECRET=

PW_STANDARD_USER_USERNAME=
PW_STANDARD_USER_PASSWORD=
PW_STANDARD_USER_2FA_SECRET=

PW_XFD_2FA_ISSUER=
PW_XFD_URL=

```

In local testing, the variables can be found at the team's Regression Testing Sharepoint. Please contact the team for details.

### **Environment Variables for Local Testing in VS Code**

If you are using testing in VS Code using the Playwright extension, add the following lines you your `settings.json`, when is accessed from `Extension Settings->Edit in settings.json`

```json
"playwright.env": {
        "PW_GLOBAL_ADMIN_USERNAME": "",
        "PW_GLOBAL_ADMIN_PASSWORD": "",
        "PW_GLOBAL_ADMIN_2FA_SECRET": "",
        "PW_REGIONAL_ADMIN_USERNAME": "",
        "PW_REGIONAL_ADMIN_PASSWORD": "",
        "PW_REGIONAL_ADMIN_2FA_SECRET": "",
        "PW_GLOBAL_VIEW_USERNAME": "",
        "PW_GLOBAL_VIEW_PASSWORD": "",
        "PW_GLOBAL_VIEW_2FA_SECRET": "",
        "PW_STANDARD_USER_USERNAME": "",
        "PW_STANDARD_USER_PASSWORD": "",
        "PW_STANDARD_USER_2FA_SECRET": "",
        "PW_XFD_2FA_ISSUER": "",
        "PW_XFD_URL": "",
}
```

## **First time use in Local Testing**

For the first time use, developers wishing to use the Playwright tests or develop new ones should first read the documentation located at: [Playwright installation guide](https://playwright.dev/docs/intro#installing-playwright).

Begin installation at the `xfd/playwright` directory by first running `npx playwright install`.

After this is done, pull down a copy `.env` file from the team Sharepoint. Place it in the `xfd/playwright` directory. This will provide you with the credentials needed to run the tests.

Once that is performed, run `source .env` to load the variables in your terminal instance. Optionally, you can include them in your `.bashrc` or `.zshrc` file to have them persist.

Open up the file `2FA.png` on the team Sharepoint and scan the QR code into a mobile authenticator. This will load the 2FA tokens for all 4 service accounts. If this doesn't work, you can use the 2FA keys found in the `.env` and manually type them into an authenticator app like Google Authenticator.

For the first time use, you will need to manually log in to each user account one time to set the row in the database, using username/password and the 2FA token. If your own developer account is a global administrator, you can then approve the 4 service account users and set them to their appropriate role. Or you can use your DBeaver database management tool and approve and set the user role type in the `Users` table.

After all 4 service accounts have been set up for the first time, you can then run Playwright via the `npx playwright test` command and it will perform the tests as expected.

## **GitHub Actions Testing with Amazon ECS**

In this mode, the Playwright tests are run everytime changes are committed to the develop and integration branches `xfd/frontend/` directory, or to the `xfd/.github/workflows/regression.yml` file itself. The Regression Testing workflow (which so far only encompasses Playwright) calls out to a containerized version of Crossfeed's Playwright testing suite stored on Amazon ECR via an ECS task. When the task is triggered, Playwright ECS will run against either the staging-cd or integration instances of Playwright. Test results are stored in Amazon S3 bucket and downloaded as artifacts to the GitHub Actions workflow.

There is no need for any frontend developer to alter any configuration of Playwright ECS. The entire configuration is set by the workflow process.

## **Logging into Crossfeed and Preserving Browser State**

The global setup script located at `xfd/playwright/global-setup.ts` performs the task of logging into Crossfeed for each uer role and storing the browsers state to `xfd/playwright/${role}.json`, where `role` can be one of [`global-admin`, `regional-admin`, `global-view`, `standard-user`]. This script works by manually performing the steps to login to Crossfeed through the browser.

This process does not use the PIV card certificate process, but a username/password process with 2FA tokens. The necessary environment variables are not stored in code, but populated by the build process (manually setting environment variables, set by docker-compose, or populated by GitHub Actions).

The `OTPAuth` module is used to generate the 2FA token needed for login, using a 2FA secret string that is not released publically.

If the global setup script fails to login, manually check the login process by logging in with the service account username/password and 2FA combo. If the Okta login process is slightly different than from what the script is anticipating, it will fail. Sometimes logging in can resolve some extra menus or checkboxes that may occassionally pop up. Unfortunately since we don't own the process, our ability to login in an automated manner is somewhat fragile.

## **Adding Test Cases**

Test cases are added by adding `*.spec.ts` files under the `xfd/playwright/e2e` folder.

Tests are defined to receive an page argument with the login state for one of the four available user roles [`pageAsGlobalAdmin`, `pageAsRegionalAdmin`, `pageAsGlobalView`, `pageAsStandardUser`]. The test case will then run as the provided user.

```typescript
test('Global Admin: homepage accessibility', async ({
    pageAsGlobalAdmin,
    makeAxeBuilder
  }, testInfo: TestInfo) => {
    await runAccessibilityTest(
      pageAsGlobalAdmin,
      makeAxeBuilder,
      testInfo,
      'Global Admin'
    );
  });
  ```

## **Test Results**

  Test results are written out to `xfd/playwright/playwright-report`. The most recent run is written out to `html/index.html` for the HTML version, and `results.json` for the latest JSON test report data.
