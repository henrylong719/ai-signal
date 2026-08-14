import { expect, test } from '@playwright/test'
import { createUser } from './utils/privateApi.ts'
import { randomEmail, randomPassword } from './utils/random'
import { logInUser } from './utils/user'

// Relative, deliberately. `page.request` shares the browser context's
// cookie jar, and the auth cookies are host-only for the app's own origin
// — an absolute backend URL here would be sent unauthenticated.
const DIGEST_PREFERENCES_PATH = '/api/v1/users/me/digest-preferences'
const ME_PATH = '/api/v1/users/me'

test.describe('Daily digest timezone sync', () => {
  test.use({
    storageState: { cookies: [], origins: [] },
    timezoneId: 'Australia/Sydney',
  })

  test('updates a moved user from their old saved timezone on app load', async ({
    page,
  }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.request.put(DIGEST_PREFERENCES_PATH, {
      data: {
        daily_digest_enabled: true,
        timezone: 'America/Chicago',
      },
    })

    await page.goto('/')

    await expect
      .poll(async () => {
        const response = await page.request.get(ME_PATH)
        return (await response.json()).timezone
      })
      .toBe('Australia/Sydney')
  })
})
