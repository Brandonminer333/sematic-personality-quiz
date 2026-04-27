import { test, expect } from '@playwright/test';

test('full quiz flow renders a result card', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('text=START QUIZ ▶')).toBeVisible();
  await page.click('text=START QUIZ ▶');

  for (let i = 0; i < 15; i += 1) {
    await expect(page.locator(`text=QUESTION ${i + 1} OF 15`)).toBeVisible();
    await page.click('.option-btn:first-of-type');
    await page.click('text=NEXT QUESTION ▶');
  }

  await expect(page.locator('.result-card')).toBeVisible();
  await expect(page.locator('.result-headline')).not.toBeEmpty();
  await expect(page.locator('.result-type')).not.toBeEmpty();
  await expect(page.locator('.type-tag')).not.toBeEmpty();
});
