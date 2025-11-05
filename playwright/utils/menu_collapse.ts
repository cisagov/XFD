import { expect } from '@playwright/test';
import type { Page, Locator } from '@playwright/test';

export async function openMenuIfCollapsed(page: Page) {
  const trigger = page
    .getByRole('button', { name: /menu|open.*menu|navigation/i })
    .first();
  if (await trigger.isVisible()) {
    await trigger.click();
    await expect(
      page.getByRole('dialog', { name: /navigation menu/i })
    ).toBeVisible();
  }
}

export async function navScope(page: Page): Promise<Locator> {
  const dialogNav = page.getByRole('dialog', { name: /navigation menu/i });
  if (await dialogNav.isVisible()) {
    return dialogNav.getByRole('navigation', { name: /main navigation/i });
  }
  return page.getByRole('navigation', { name: /main navigation/i });
}
