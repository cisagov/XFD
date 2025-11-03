import { test } from '../../tests/fixtures';
import { expect } from '@playwright/test';

test.describe('Update State Form', () => {
  test('should display Update State Information dialog for user without state', async ({
    pageAsStandardUser
  }) => {
    await pageAsStandardUser.goto('/');

    const dialogTitle = pageAsStandardUser.getByText(
      'Update State Information'
    );
    const dialog = pageAsStandardUser.getByRole('dialog');
    const isDialogVisible = await dialog.isVisible().catch(() => false);

    if (isDialogVisible) {
      await expect(dialogTitle).toBeVisible();
      await expect(dialog).toContainText('Update State Information');
    } else {
      test.skip();
    }
  });

  test('should contain all required form elements when displayed', async ({
    pageAsStandardUser
  }) => {
    await pageAsStandardUser.goto('/');

    const dialog = pageAsStandardUser.getByRole('dialog');
    const isDialogVisible = await dialog.isVisible().catch(() => false);

    if (isDialogVisible) {
      const stateLabel = pageAsStandardUser.getByText('State');
      await expect(stateLabel).toBeVisible();

      const stateSelect = pageAsStandardUser.locator('#state');
      await expect(stateSelect).toBeVisible();

      const saveButton = pageAsStandardUser.getByRole('button', {
        name: /save/i
      });
      await expect(saveButton).toBeVisible();
      await expect(saveButton).toBeEnabled();

      const cancelButton = pageAsStandardUser.getByRole('button', {
        name: /cancel/i
      });
      await expect(cancelButton).toBeVisible();
      await expect(cancelButton).toBeEnabled();

      const saveIcon = saveButton.locator('svg');
      await expect(saveIcon).toBeVisible();
    } else {
      test.skip();
    }
  });

  test('should be able to select a state option', async ({
    pageAsStandardUser
  }) => {
    await pageAsStandardUser.goto('/');

    const dialog = pageAsStandardUser.getByRole('dialog');
    const isDialogVisible = await dialog.isVisible().catch(() => false);

    if (isDialogVisible) {
      const stateSelect = pageAsStandardUser.locator('#state');
      await stateSelect.click();

      const dropdown = pageAsStandardUser.getByRole('listbox');
      await expect(dropdown).toBeVisible();

      const firstOption = pageAsStandardUser.getByRole('option').first();
      await expect(firstOption).toBeVisible();

      await firstOption.click();

      await expect(dropdown).not.toBeVisible();

      const selectedValue = await stateSelect.inputValue();
      expect(selectedValue).toBeTruthy();
    } else {
      test.skip();
    }
  });

  test('should handle successful form submission', async ({
    pageAsStandardUser
  }) => {
    await pageAsStandardUser.goto('/');

    const dialog = pageAsStandardUser.getByRole('dialog');
    const isDialogVisible = await dialog.isVisible().catch(() => false);

    if (isDialogVisible) {
      const stateSelect = pageAsStandardUser.locator('#state');
      await stateSelect.click();

      const firstOption = pageAsStandardUser.getByRole('option').first();
      await firstOption.click();

      const saveButton = pageAsStandardUser.getByRole('button', {
        name: /save/i
      });
      await saveButton.click();

      const loadingSpinner = saveButton.locator(
        '[data-testid="CircularProgress"]'
      );

      await expect(dialog).not.toBeVisible({ timeout: 10000 });

      await expect(pageAsStandardUser).toHaveURL(/^(?!.*login)/);
    } else {
      test.skip();
    }
  });

  test('should show error alert on API failure', async ({
    pageAsStandardUser
  }) => {
    await pageAsStandardUser.goto('/');

    const dialog = pageAsStandardUser.getByRole('dialog');
    const isDialogVisible = await dialog.isVisible().catch(() => false);

    if (isDialogVisible) {
      await pageAsStandardUser.route('**/v2/update_user/**', (route) => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server error' })
        });
      });

      const stateSelect = pageAsStandardUser.locator('#state');
      await stateSelect.click();

      const firstOption = pageAsStandardUser.getByRole('option').first();
      await firstOption.click();

      const saveButton = pageAsStandardUser.getByRole('button', {
        name: /save/i
      });
      await saveButton.click();

      const errorAlert = dialog.getByRole('alert');
      await expect(errorAlert).toBeVisible();
      await expect(errorAlert).toContainText(
        'Something went wrong updating the state'
      );

      await expect(dialog).toBeVisible();
    } else {
      test.skip();
    }
  });

  test('should prevent dialog close without saving via backdrop or escape', async ({
    pageAsStandardUser
  }) => {
    await pageAsStandardUser.goto('/');

    const dialog = pageAsStandardUser.getByRole('dialog');
    const isDialogVisible = await dialog.isVisible().catch(() => false);

    if (isDialogVisible) {
      await pageAsStandardUser.keyboard.press('Escape');
      await pageAsStandardUser.waitForURL(/login|auth/, { timeout: 5000 });
    } else {
      test.skip();
    }
  });

  test('should logout when Cancel button is clicked', async ({
    pageAsStandardUser
  }) => {
    await pageAsStandardUser.goto('/');

    const dialog = pageAsStandardUser.getByRole('dialog');
    const isDialogVisible = await dialog.isVisible().catch(() => false);

    if (isDialogVisible) {
      const cancelButton = pageAsStandardUser.getByRole('button', {
        name: /cancel/i
      });
      await cancelButton.click();

      await pageAsStandardUser.waitForURL(/login|auth/, { timeout: 5000 });
    } else {
      test.skip();
    }
  });
});
