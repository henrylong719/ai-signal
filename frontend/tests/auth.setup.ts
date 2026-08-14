import { test as setup } from '@playwright/test'
import { firstSuperuser, firstSuperuserPassword } from './config.ts'
import { openEmailAuthForm } from './utils/auth-form.ts'

const authFile = 'playwright/.auth/user.json'

setup('authenticate', async ({ page }) => {
  await page.goto('/login')
  await openEmailAuthForm(page)
  await page.getByTestId('email-input').fill(firstSuperuser)
  await page.getByTestId('password-input').fill(firstSuperuserPassword)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await page.waitForURL('/')
  await page.context().storageState({ path: authFile })
})
