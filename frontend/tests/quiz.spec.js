import { test, expect } from '@playwright/test';

// The frontend now calls a FastAPI backend for classification. This spec
// mocks that call so the test stays a pure frontend smoke test (no backend
// needs to be running). The full backend+frontend wiring is exercised by
// `tests/test_integration.py`.
test('full quiz flow renders a result card', async ({ page }) => {
  await page.route('**/classify', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        type: 'Rock',
        ranking: [{ type: 'Rock', score: 1.0 }],
      }),
    });
  });

  await page.goto('/');
  await expect(page.locator('text=START QUIZ ▶')).toBeVisible();
  await page.click('text=START QUIZ ▶');

  for (let i = 0; i < 15; i += 1) {
    await expect(page.locator(`text=QUESTION ${i + 1} OF 15`)).toBeVisible();
    await page.click('.option-btn:first-of-type');
    await page.locator('.next-btn').click();
  }

  await expect(page.locator('.result-card')).toBeVisible();
  await expect(page.locator('.result-headline')).not.toBeEmpty();
  await expect(page.locator('.result-type')).not.toBeEmpty();
  await expect(page.locator('.type-tag')).not.toBeEmpty();
});
