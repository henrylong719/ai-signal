import { expect, type Page, test } from '@playwright/test'

test.use({ storageState: { cookies: [], origins: [] } })

async function stubSignedInDashboard(page: Page) {
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
        email: 'reader@example.com',
        is_active: true,
        is_superuser: false,
        full_name: 'Signal Reader',
        has_password: true,
        created_at: '2026-05-08T12:00:00Z',
        // Load-bearing. A null onboarded_at mounts the first-run
        // onboarding modal, which covers the header (so "Open profile
        // menu" stops matching) and fetches /users/me/interests — which
        // is not stubbed here, 401s, and sends the auth interceptor
        // redirecting to /login.
        onboarded_at: '2026-05-08T12:00:00Z',
      },
    })
  })
  await page.route('**/api/v1/articles/saved/ids', async (route) => {
    await route.fulfill({ json: { article_ids: [] } })
  })
  // The `/` route itself calls useInterests(), which is gated on the
  // marker cookie this helper sets. Leaving it unstubbed means a real
  // 401 and the auth interceptor navigating away to /login.
  await page.route('**/api/v1/users/me/interests', async (route) => {
    await route.fulfill({
      json: {
        categories: [],
        tags: [],
        preferred_sources: [],
        updated_at: null,
      },
    })
  })
  await page.route('**/api/v1/articles/for-you?*', async (route) => {
    await route.fulfill({
      json: { data: [], count: 0, candidate_pool_cap: 200 },
    })
  })
  await page.route('**/api/v1/articles/?*', async (route) => {
    await route.fulfill({ json: { data: [], count: 0 } })
  })
  // Sibling of the For You tab, and not covered by the `/articles/?*`
  // pattern above. Unstubbed it 401s under this fake session and the
  // auth interceptor redirects to /login.
  await page.route('**/api/v1/articles/following?*', async (route) => {
    await route.fulfill({ json: { data: [], count: 0 } })
  })
}

test('signed-in user can submit feedback from the profile menu', async ({
  page,
}) => {
  await stubSignedInDashboard(page)

  let submittedBody: unknown
  await page.route('**/api/v1/users/me/feedback', async (route) => {
    submittedBody = route.request().postDataJSON()
    await route.fulfill({
      status: 201,
      json: {
        id: '33333333-3333-4333-8333-333333333333',
        user_id: '22222222-2222-4222-8222-222222222222',
        category: 'bug_report',
        message: 'The recommendation dismissal button felt unclear.',
        context: { path: '/', title: 'AI Signal', source: 'profile_menu' },
        created_at: '2026-05-08T12:00:00Z',
        updated_at: '2026-05-08T12:00:00Z',
      },
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Open profile menu' }).click()
  await page.getByRole('menuitem', { name: 'Feedback' }).click()

  await expect(
    page.getByRole('dialog', { name: 'Share your feedback' }),
  ).toBeVisible()

  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByText('Add at least 10 characters.')).toBeVisible()

  await page.getByRole('combobox').click()
  await page.getByRole('option', { name: 'Bug report' }).click()
  await page
    .getByLabel('Message')
    .fill('The recommendation dismissal button felt unclear.')
  await page.getByRole('button', { name: 'Send' }).click()

  await expect(page.getByText('Thanks. Your feedback was sent.')).toBeVisible()
  expect(submittedBody).toMatchObject({
    category: 'bug_report',
    message: 'The recommendation dismissal button felt unclear.',
    context: expect.objectContaining({ path: '/', source: 'profile_menu' }),
  })
})
