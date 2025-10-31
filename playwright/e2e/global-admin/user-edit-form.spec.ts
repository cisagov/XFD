import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';

test.describe('User Edit Form - Global Admin', () => {
  test('Global Admin: user edit state dropdown enabled', async ({
    pageAsGlobalAdmin
  }) => {
    await pageAsGlobalAdmin.goto('/users');
    await pageAsGlobalAdmin
      .getByRole('button', { name: 'View or Edit User Sample User' })
      .first()
      .click();
    await expect(pageAsGlobalAdmin.locator('#state')).toBeEnabled();
  });
});

test.describe('User Edit Form - Regional Admin', () => {
  test('Regional Admin: user edit state dropdown disabled', async ({
    pageAsRegionalAdmin
  }) => {
    await pageAsRegionalAdmin.goto('/users');
    await pageAsRegionalAdmin
      .getByRole('button', { name: 'View or Edit User Sample User' })
      .first()
      .click();
    await expect(pageAsRegionalAdmin.locator('#state')).toBeDisabled();
  });
});

test.describe('User Edit Form - Global View', () => {
  test('Global View: user edit state dropdown disabled', async ({
    pageAsGlobalView
  }) => {
    await pageAsGlobalView.goto('/users');
    await pageAsGlobalView
      .getByRole('button', { name: 'View or Edit User Sample User' })
      .first()
      .click();
    await expect(pageAsGlobalView.locator('#state')).toBeDisabled();
  });
});
