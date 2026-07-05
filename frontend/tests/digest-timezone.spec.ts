import { expect, test } from '@playwright/test'
import { createUser } from './utils/privateApi.ts'
import { randomEmail, randomPassword } from './utils/random'
import { logInUser } from './utils/user'

const apiBase = process.env.VITE_API_URL

test.describe('Daily digest timezone sync', () => {
  test.use({
    storageState: { cookies: [], origins: [] },
    timezoneId: 'Australia/Sydney',
  })

  test('updates a moved user from their old saved timezone on app load', async ({
    page,
  }) => {
    expect(apiBase, 'VITE_API_URL is required for API assertions').toBeTruthy()

    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.request.put(`${apiBase}/api/v1/users/me/digest-preferences`, {
      data: {
        daily_digest_enabled: true,
        timezone: 'America/Chicago',
      },
    })

    await page.goto('/')

    await expect
      .poll(async () => {
        const response = await page.request.get(`${apiBase}/api/v1/users/me`)
        return (await response.json()).timezone
      })
      .toBe('Australia/Sydney')
  })
})
