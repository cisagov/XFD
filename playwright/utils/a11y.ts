import { expect, type Page, type TestInfo } from '@playwright/test';

export async function runAxeAndFailOnSerious(
  page: Page,
  makeAxeBuilder: (page: Page) => any,
  testInfo: TestInfo,
  label: string
) {
  const axe = makeAxeBuilder(page);
  const results = await axe.analyze();

  await testInfo.attach(`${label} — axe-results`, {
    body: JSON.stringify(results, null, 2),
    contentType: 'application/json'
  });

  const bad = results.violations.filter((v: any) =>
    ['serious', 'critical'].includes(v.impact)
  );

  expect(
    bad,
    `${label} a11y violations (serious/critical):\n` +
      JSON.stringify(bad, null, 2)
  ).toHaveLength(0);
}
