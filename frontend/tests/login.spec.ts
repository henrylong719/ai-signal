import { expect, type Page, test } from '@playwright/test'
import { firstSuperuser, firstSuperuserPassword } from './config.ts'
import { openEmailAuthForm } from './utils/auth-form.ts'
import { randomPassword } from './utils/random.ts'

test.use({ storageState: { cookies: [], origins: [] } })

const fillForm = async (page: Page, email: string, password: string) => {
  await openEmailAuthForm(page)
  await page.getByTestId('email-input').fill(email)
  await page.getByTestId('password-input').fill(password)
}

const verifyInput = async (page: Page, testId: string) => {
  const input = page.getByTestId(testId)
  await expect(input).toBeVisible()
  await expect(input).toHaveText('')
  await expect(input).toBeEditable()
}

test('Inputs are visible, empty and editable', async ({ page }) => {
  await page.goto('/login')
  await openEmailAuthForm(page)

  await verifyInput(page, 'email-input')
  await verifyInput(page, 'password-input')
})

test('Sign In button is visible', async ({ page }) => {
  await page.goto('/login')
  await openEmailAuthForm(page)

  await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
})

test('Auth method options are visible before email form', async ({ page }) => {
  await page.goto('/login')

  await expect(
    page.getByRole('button', { name: 'Continue with Google' }),
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Continue with GitHub' }),
  ).toBeVisible()
  // Facebook is deliberately commented out in SocialLoginButtons — assert
  // it stays gone so re-enabling it is a conscious test change.
  await expect(
    page.getByRole('button', { name: 'Continue with Facebook' }),
  ).toBeHidden()
  await expect(
    page.getByRole('button', { name: 'Continue with email' }),
  ).toBeVisible()
  await expect(page.getByTestId('email-input')).toBeHidden()
})

test('Forgot Password link is visible', async ({ page }) => {
  await page.goto('/login')
  await openEmailAuthForm(page)

  await expect(
    page.getByRole('link', { name: 'Forgot password?' }),
  ).toBeVisible()
})

test('Log in with valid email and password ', async ({ page }) => {
  await page.goto('/login')

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole('button', { name: 'Sign In' }).click()

  await page.waitForURL('/')

  await expect(
    page.getByRole('button', { name: 'Open profile menu' }),
  ).toBeVisible()
})

test('Log in with invalid email', async ({ page }) => {
  await page.goto('/login')

  await fillForm(page, 'invalidemail', firstSuperuserPassword)
  await page.getByRole('button', { name: 'Sign In' }).click()

  await expect(page.getByText('Invalid email address')).toBeVisible()
})

test('Log in with invalid password', async ({ page }) => {
  const password = randomPassword()

  await page.goto('/login')
  await fillForm(page, firstSuperuser, password)
  await page.getByRole('button', { name: 'Sign In' }).click()

  await expect(page.getByText('Incorrect email or password')).toBeVisible()
})

test('Successful log out', async ({ page }) => {
  await page.goto('/login')

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole('button', { name: 'Sign In' }).click()

  await page.waitForURL('/')

  await expect(
    page.getByRole('button', { name: 'Open profile menu' }),
  ).toBeVisible()

  await page.getByRole('button', { name: 'Open profile menu' }).click()
  await page.getByRole('menuitem', { name: 'Log out' }).click()
  await page.waitForURL('/')
  // Scoped to the header: the logged-out landing page carries more than
  // one "Sign In" button, and it's the header one that proves the logout.
  await expect(
    page.getByRole('banner').getByRole('button', { name: 'Sign In' }),
  ).toBeVisible()
})

test('Logged-out user cannot access protected routes', async ({ page }) => {
  await page.goto('/login')

  await fillForm(page, firstSuperuser, firstSuperuserPassword)
  await page.getByRole('button', { name: 'Sign In' }).click()

  await page.waitForURL('/')

  await expect(
    page.getByRole('button', { name: 'Open profile menu' }),
  ).toBeVisible()

  await page.getByRole('button', { name: 'Open profile menu' }).click()
  await page.getByRole('menuitem', { name: 'Log out' }).click()
  await page.waitForURL('/')

  await page.goto('/settings')
  await expect(page.getByText('Sign in to manage settings')).toBeVisible()
})

test('Logged-out settings page shows sign-in prompt', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByText('Sign in to manage settings')).toBeVisible()
})
