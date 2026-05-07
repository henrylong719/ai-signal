import { expect, type Page, test } from '@playwright/test'

const article = {
  id: '11111111-1111-4111-8111-111111111111',
  url: 'https://example.com/for-you',
  title: 'Personalized ranking update',
  source: 'Example',
  excerpt: 'A short summary.',
  image_url: null,
  author: null,
  category: 'models',
  tags: ['models'],
  published_at: '2026-05-07T12:00:00Z',
  fetched_at: '2026-05-07T12:00:00Z',
  reason: 'Because you follow models',
}

test.use({ storageState: { cookies: [], origins: [] } })

async function stubDashboardApis(page: Page, candidatePoolCap: number) {
  await page.context().addCookies([
    {
      name: 'is_logged_in',
      value: '1',
      url: 'http://localhost:5173',
    },
  ])
  await page.route('**/api/v1/users/me', async (route) => {
    await route.fulfill({
      json: {
        id: '22222222-2222-4222-8222-222222222222',
        email: 'user@example.com',
        is_active: true,
        is_superuser: false,
        full_name: 'Test User',
        has_password: true,
        created_at: '2026-05-07T12:00:00Z',
      },
    })
  })
  await page.route('**/api/v1/articles/saved/ids', async (route) => {
    await route.fulfill({ json: { article_ids: [] } })
  })
  await page.route('**/api/v1/articles/for-you?*', async (route) => {
    await route.fulfill({
      json: {
        data: [article],
        count: 1,
        candidate_pool_cap: candidatePoolCap,
      },
    })
  })
  await page.route('**/api/v1/articles/?*', async (route) => {
    await route.fulfill({ json: { data: [], count: 0 } })
  })
}

test('For You feed shows capped-pool message at the candidate cap', async ({
  page,
}) => {
  await stubDashboardApis(page, 1)

  await page.goto('/')

  await expect(
    page.getByText("That's all your top picks for now."),
  ).toBeVisible()
  await expect(page.getByText("You're all caught up.")).not.toBeVisible()
})

test('For You feed keeps all-caught-up message below the candidate cap', async ({
  page,
}) => {
  await stubDashboardApis(page, 200)

  await page.goto('/')

  await expect(page.getByText("You're all caught up.")).toBeVisible()
  await expect(
    page.getByText("That's all your top picks for now."),
  ).not.toBeVisible()
})
