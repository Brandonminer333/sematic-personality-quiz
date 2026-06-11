import { test, expect } from '@playwright/test';

const MOCK_QUIZ_ID = 'test-quiz-id';
const MOCK_RESULT = {
  type: 'Gryffindor',
  ranking: [
    { type: 'Gryffindor', score: 0.8 },
    { type: 'Slytherin', score: -0.2 },
  ],
  closest_character: {
    name: 'Harry Potter',
    class: 'Gryffindor',
    score: 0.95,
  },
  projection: {
    user: { x: 0.1, y: 0.2, z: 0.3 },
    leaders: [
      { name: 'Harry Potter', type: 'Gryffindor', x: 0.2, y: 0.1, z: 0.0 },
      { name: 'Draco Malfoy', type: 'Slytherin', x: -0.2, y: -0.1, z: 0.0 },
    ],
  },
  quiz_id: MOCK_QUIZ_ID,
};

test('full quiz flow renders a result card', async ({ page }) => {
  await page.route('**/quizzes', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify({
          quiz_id: MOCK_QUIZ_ID,
          status: 'generating',
          title: 'Harry Potter',
          classes: ['Gryffindor', 'Slytherin'],
        }),
      });
      return;
    }
    await route.continue();
  });

  await page.route(`**/quizzes/${MOCK_QUIZ_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        quiz_id: MOCK_QUIZ_ID,
        status: 'ready',
        title: 'Harry Potter',
        classes: ['Gryffindor', 'Slytherin'],
        progress: { completed: 2, total: 2 },
        error: null,
      }),
    });
  });

  await page.route('**/quiz_results', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_RESULT),
    });
  });

  await page.goto('/');
  const prompt = page.getByRole('textbox', { name: 'Your prompt' });
  await prompt.fill('Hogwarts houses');
  await expect(prompt).toHaveValue('Hogwarts houses');
  await page.getByRole('button', { name: /CREATE QUIZ/ }).click();
  await page.waitForURL(`**/quiz/${MOCK_QUIZ_ID}`, { timeout: 10000 });

  for (let i = 0; i < 15; i += 1) {
    await expect(page.locator(`text=QUESTION ${i + 1} OF 15`)).toBeVisible();
    await page.click('.option-btn:first-of-type');
    await page.locator('.next-btn').click();
  }

  await page.waitForURL(`**/quiz/${MOCK_QUIZ_ID}/results`, { timeout: 10000 });
  await expect(page.locator('.result-card')).toBeVisible();
  await expect(page.locator('.result-type')).toContainText('Gryffindor');
});
