import { expect, test } from '@playwright/test'
import { randomEmail, randomPassword } from './utils/random'
import {
  extractResetPasswordPath,
  fetchRecoveryEmailHtml,
} from './utils/recoveryEmail'
import { logInUser, signUpNewUser } from './utils/user'

test.use({ storageState: { cookies: [], origins: [] } })

test('Password Recovery title is visible', async ({ page }) => {
  await page.goto('/recover-password')

  await expect(
    page.getByRole('heading', { name: 'Reset your password' }),
  ).toBeVisible()
})

test('Input is visible, empty and editable', async ({ page }) => {
  await page.goto('/recover-password')

  await expect(page.getByTestId('email-input')).toBeVisible()
  await expect(page.getByTestId('email-input')).toHaveText('')
  await expect(page.getByTestId('email-input')).toBeEditable()
})

test('Send reset link button is visible', async ({ page }) => {
  await page.goto('/recover-password')

  await expect(
    page.getByRole('button', { name: 'Send reset link' }),
  ).toBeVisible()
})

test('User can reset password successfully using the link', async ({
  page,
  request,
}) => {
  const fullName = 'Test User'
  const email = randomEmail()
  const password = randomPassword()
  const newPassword = randomPassword()

  // Sign up a new user
  await signUpNewUser(page, fullName, email, password)

  await page.goto('/recover-password')
  await page.getByTestId('email-input').fill(email)

  await page.getByRole('button', { name: 'Send reset link' }).click()
  await expect(
    page.getByText('Recovery email sent. Check your inbox.'),
  ).toBeVisible()

  const resetPath = extractResetPasswordPath(
    await fetchRecoveryEmailHtml(request, email),
  )

  // Set the new password and confirm it
  await page.goto(resetPath)

  await page.getByTestId('new-password-input').fill(newPassword)
  await page.getByTestId('confirm-password-input').fill(newPassword)
  await page.getByRole('button', { name: 'Update password' }).click()
  await expect(
    page.getByText('Password updated. You can sign in now.'),
  ).toBeVisible()

  // Check if the user is able to login with the new password
  await logInUser(page, email, newPassword)
})

test('Expired or invalid reset link', async ({ page }) => {
  const password = randomPassword()
  const invalidUrl = '/reset-password?token=invalidtoken'

  await page.goto(invalidUrl)

  await page.getByTestId('new-password-input').fill(password)
  await page.getByTestId('confirm-password-input').fill(password)
  await page.getByRole('button', { name: 'Update password' }).click()

  await expect(page.getByText('Invalid token')).toBeVisible()
})

test('Weak new password validation', async ({ page, request }) => {
  const fullName = 'Test User'
  const email = randomEmail()
  const password = randomPassword()
  const weakPassword = '123'

  // Sign up a new user
  await signUpNewUser(page, fullName, email, password)

  await page.goto('/recover-password')
  await page.getByTestId('email-input').fill(email)
  await page.getByRole('button', { name: 'Send reset link' }).click()
  await expect(
    page.getByText('Recovery email sent. Check your inbox.'),
  ).toBeVisible()

  const resetPath = extractResetPasswordPath(
    await fetchRecoveryEmailHtml(request, email),
  )

  // Set a weak new password
  await page.goto(resetPath)
  await page.getByTestId('new-password-input').fill(weakPassword)
  await page.getByTestId('confirm-password-input').fill(weakPassword)
  await page.getByRole('button', { name: 'Update password' }).click()

  await expect(
    page.getByText('Password must be at least 8 characters'),
  ).toBeVisible()
})
