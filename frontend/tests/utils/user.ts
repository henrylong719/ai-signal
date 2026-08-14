import { expect, type Page } from '@playwright/test'
import { openEmailAuthForm } from './auth-form'
import { completeOnboarding } from './onboarding'

export async function signUpNewUser(
  page: Page,
  name: string,
  email: string,
  password: string,
) {
  await page.goto('/signup')
  await openEmailAuthForm(page)

  // No confirm-password field: SignUpScreen dropped it when the provider
  // step landed. sign-up.spec.ts was updated then; this helper was not.
  await page.getByTestId('full-name-input').fill(name)
  await page.getByTestId('email-input').fill(email)
  await page.getByTestId('password-input').fill(password)
  await page.getByRole('button', { name: 'Create Account' }).click()

  // POST /users/signup issues a session, so a successful signup lands on
  // the feed already signed in. Navigating straight to /login raced that
  // response: sometimes the user was not created yet (later steps 404),
  // sometimes the cookie arrived first and /login bounced back to /.
  // Wait for the landing, clear onboarding, then log out — callers all
  // expect to be back on /login with a user that definitely exists.
  await page.waitForURL('/')
  await completeOnboarding(page)
  await logOutUser(page)
}

export async function logInUser(page: Page, email: string, password: string) {
  await page.goto('/login')
  await openEmailAuthForm(page)

  await page.getByTestId('email-input').fill(email)
  await page.getByTestId('password-input').fill(password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await page.waitForURL('/')
  await completeOnboarding(page)
  await expect(
    page.getByRole('button', { name: 'Open profile menu' }),
  ).toBeVisible()
}

export async function logOutUser(page: Page) {
  await page.getByRole('button', { name: 'Open profile menu' }).click()
  await page.getByRole('menuitem', { name: 'Log out' }).click()
  // logout() awaits the server call, clears the marker cookie, then
  // navigates to /. Wait for the logged-out header before going anywhere:
  // navigating too early leaves the cookie set, and /login and
  // /recover-password both bounce a "logged in" visitor back to the feed.
  await expect(
    page.getByRole('banner').getByRole('button', { name: 'Sign In' }),
  ).toBeVisible()
  await page.goto('/login')
}
