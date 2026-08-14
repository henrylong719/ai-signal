import { test as setup } from '@playwright/test'
import { firstSuperuser, firstSuperuserPassword } from './config.ts'
import { openEmailAuthForm } from './utils/auth-form.ts'
import { completeOnboarding } from './utils/onboarding.ts'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  await page.goto('/login')
  await openEmailAuthForm(page)
  await page.getByTestId('email-input').fill(firstSuperuser)
  await page.getByTestId('password-input').fill(firstSuperuserPassword)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await page.waitForURL('/')
  // Otherwise every spec that reuses this storage state opens on the
  // first-run onboarding modal.
  await completeOnboarding(page)
  await page.context().storageState({ path: authFile })
})
