# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: quiz.spec.js >> full quiz flow submits answers and shows a result
- Location: tests/quiz.spec.js:14:1

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5173/
Call log:
  - navigating to "http://127.0.0.1:5173/", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | const resultResponse = {
  4  |   emoji: '🔥',
  5  |   type: 'FIRE TYPE',
  6  |   headline: 'The Blazing Trailblazer',
  7  |   tag: 'Fire Type',
  8  |   desc: 'You burn bright and inspire everyone around you. Passionate, bold, and impossible to ignore — you lead with your heart and light up every room you enter. You\'re not afraid to take risks, and that fearless energy is contagious.',
  9  |   traits: ['Bold', 'Passionate', 'Inspirational', 'Energetic'],
  10 |   famous: 'Blaine — the Volcano Badge gym leader, a fiery quiz master who tests the bold.',
  11 |   color: '#ff6b35',
  12 | };
  13 | 
  14 | test('full quiz flow submits answers and shows a result', async ({ page }) => {
  15 |   let submitPayload = null;
  16 | 
  17 |   await page.route('**/submit_answers', async (route) => {
  18 |     const request = route.request();
  19 |     submitPayload = await request.postDataJSON();
  20 |     await route.fulfill({
  21 |       status: 200,
  22 |       contentType: 'application/json',
  23 |       body: JSON.stringify({ message: 'Answers submitted' }),
  24 |     });
  25 |   });
  26 | 
  27 |   await page.route('**/result', async (route) => {
  28 |     await route.fulfill({
  29 |       status: 200,
  30 |       contentType: 'application/json',
  31 |       body: JSON.stringify(resultResponse),
  32 |     });
  33 |   });
  34 | 
> 35 |   await page.goto('/');
     |              ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5173/
  36 |   await expect(page.locator('text=START QUIZ ▶')).toBeVisible();
  37 |   await page.click('text=START QUIZ ▶');
  38 | 
  39 |   for (let i = 0; i < 15; i += 1) {
  40 |     await expect(page.locator(`text=QUESTION ${i + 1} OF 15`)).toBeVisible();
  41 |     await page.click('.option-btn:first-of-type');
  42 |     await page.click('text=NEXT QUESTION ▶');
  43 |   }
  44 | 
  45 |   await expect(page.locator('.result-card')).toBeVisible();
  46 |   await expect(page.locator('.result-headline')).toHaveText(resultResponse.headline);
  47 |   await expect(page.locator('.result-type')).toHaveText(resultResponse.type);
  48 |   await expect(page.locator('.type-tag')).toHaveText(resultResponse.tag);
  49 | 
  50 |   expect(Array.isArray(submitPayload)).toBe(true);
  51 |   expect(submitPayload).toHaveLength(15);
  52 |   expect(submitPayload[0]).toBe('strongly disagree');
  53 | });
  54 | 
```