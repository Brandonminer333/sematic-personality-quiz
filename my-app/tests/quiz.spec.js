import { test, expect } from '@playwright/test';

const resultResponse = {
  emoji: '🔥',
  type: 'FIRE TYPE',
  headline: 'The Blazing Trailblazer',
  tag: 'Fire Type',
  desc: 'You burn bright and inspire everyone around you. Passionate, bold, and impossible to ignore — you lead with your heart and light up every room you enter. You\'re not afraid to take risks, and that fearless energy is contagious.',
  traits: ['Bold', 'Passionate', 'Inspirational', 'Energetic'],
  famous: 'Blaine — the Volcano Badge gym leader, a fiery quiz master who tests the bold.',
  color: '#ff6b35',
};

test('full quiz flow submits answers and shows a result', async ({ page }) => {
  let submitPayload = null;

  await page.route('**/submit_answers', async (route) => {
    const request = route.request();
    submitPayload = await request.postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'Answers submitted' }),
    });
  });

  await page.route('**/result', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(resultResponse),
    });
  });

  await page.goto('/');
  await expect(page.locator('text=START QUIZ ▶')).toBeVisible();
  await page.click('text=START QUIZ ▶');

  for (let i = 0; i < 15; i += 1) {
    await expect(page.locator(`text=QUESTION ${i + 1} OF 15`)).toBeVisible();
    await page.click('.option-btn:first-of-type');
    await page.click('text=NEXT QUESTION ▶');
  }

  await expect(page.locator('.result-card')).toBeVisible();
  await expect(page.locator('.result-headline')).toHaveText(resultResponse.headline);
  await expect(page.locator('.result-type')).toHaveText(resultResponse.type);
  await expect(page.locator('.type-tag')).toHaveText(resultResponse.tag);

  expect(Array.isArray(submitPayload)).toBe(true);
  expect(submitPayload).toHaveLength(15);
  expect(submitPayload[0]).toBe('strongly disagree');
});
