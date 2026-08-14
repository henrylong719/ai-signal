import { expect, type Page, test } from '@playwright/test'
import { firstSuperuser, firstSuperuserPassword } from './config.ts'
import { createUser } from './utils/privateApi.ts'
import { randomEmail, randomPassword } from './utils/random'
import { logInUser, logOutUser } from './utils/user'

// The settings page dropped its tab bar for a single scrolling page of
// titled sections. These are those section headings, in render order.
const sections = [
  'Profile Information',
  'Password & Security',
  'Sign-in Methods',
  'Daily Digest',
  'Danger Zone',
]

/**
 * Pick a theme from the profile menu's Appearance submenu.
 *
 * The theme control used to be a `theme-button` in the sidebar. It now
 * lives behind the header avatar, so every theme assertion has to open
 * two levels of menu first.
 */
async function selectTheme(
  page: Page,
  label: 'Light' | 'Dark' | 'System Default',
) {
  await page.getByRole('button', { name: 'Open profile menu' }).click()
  await page.getByRole('menuitem', { name: 'Appearance' }).click()
  await page.getByRole('menuitem', { name: label, exact: true }).click()
}

test('Settings page opens on the profile section', async ({ page }) => {
  await page.goto('/settings')

  await expect(
    page.getByRole('heading', { name: 'Account Settings' }),
  ).toBeVisible()
  await expect(
    page.getByRole('heading', { name: 'Profile Information' }),
  ).toBeVisible()
})

test('All settings sections are visible', async ({ page }) => {
  await page.goto('/settings')
  for (const section of sections) {
    await expect(page.getByRole('heading', { name: section })).toBeVisible()
  }
})

test.describe('Edit user profile', () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  let password: string

  test.beforeAll(async () => {
    email = randomEmail()
    password = randomPassword()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await page.goto('/settings')
  })

  test('Edit user name with a valid name', async ({ page }) => {
    const updatedName = 'Test User 2'

    await page.getByLabel('Full name').fill(updatedName)
    await page.getByRole('button', { name: 'Save profile' }).click()

    await expect(page.getByText('Account details updated.')).toBeVisible()
    await expect(page.getByLabel('Full name')).toHaveValue(updatedName)
  })

  test('Edit user email with an invalid email shows error', async ({
    page,
  }) => {
    await page.getByLabel('Email address').fill('')
    await page.locator('body').click()

    await expect(page.getByText('Invalid email address')).toBeVisible()
  })
})

test.describe('Edit user email', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('Edit user email with a valid email', async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    const updatedEmail = randomEmail()

    await createUser({ email, password })
    await logInUser(page, email, password)
    await page.goto('/settings')

    await page.getByLabel('Email address').fill(updatedEmail)
    await page.getByRole('button', { name: 'Save profile' }).click()

    await expect(page.getByText('Account details updated.')).toBeVisible()
    await expect(page.getByLabel('Email address')).toHaveValue(updatedEmail)
  })
})

// The profile form no longer has an Edit/Cancel pair — it is always
// editable and guards against accidental writes by keeping Save disabled
// until something changes. These cover that guard, and that an
// unsaved edit is genuinely unsaved.
test.describe('Discarding unsaved profile edits', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('Save profile is disabled until a field changes', async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })

    await logInUser(page, email, password)
    await page.goto('/settings')

    const save = page.getByRole('button', { name: 'Save profile' })
    await expect(save).toBeDisabled()

    // Not 'Test User' — that's the name createUser seeds, so the form
    // would still be pristine and Save would stay disabled.
    await page.getByLabel('Full name').fill('A Different Name')
    await expect(save).toBeEnabled()
  })

  test('Reloading restores the saved name and email', async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    const user = await createUser({ email, password })

    await logInUser(page, email, password)
    await page.goto('/settings')

    await page.getByLabel('Full name').fill('Some Other Name')
    await page.getByLabel('Email address').fill(randomEmail())
    await page.reload()

    await expect(page.getByLabel('Full name')).toHaveValue(
      user.full_name as string,
    )
    await expect(page.getByLabel('Email address')).toHaveValue(email)
  })
})

test.describe('Change password', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('Update password successfully', async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    const newPassword = randomPassword()

    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto('/settings')
    await page.getByTestId('current-password-input').fill(password)
    await page.getByTestId('new-password-input').fill(newPassword)
    await page.getByTestId('confirm-password-input').fill(newPassword)
    await page.getByRole('button', { name: 'Update password' }).click()

    await expect(page.getByText('Password updated.')).toBeVisible()

    await logOutUser(page)
    await logInUser(page, email, newPassword)
  })
})

test.describe('Change password validation', () => {
  test.use({ storageState: { cookies: [], origins: [] } })
  let email: string
  let password: string

  test.beforeAll(async () => {
    email = randomEmail()
    password = randomPassword()
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
    await page.goto('/settings')
  })

  test('Update password with weak passwords', async ({ page }) => {
    const weakPassword = 'weak'

    await page.getByTestId('current-password-input').fill(password)
    await page.getByTestId('new-password-input').fill(weakPassword)
    await page.getByTestId('confirm-password-input').fill(weakPassword)
    await page.getByRole('button', { name: 'Update password' }).click()

    await expect(
      page.getByText('Password must be at least 8 characters').first(),
    ).toBeVisible()
  })

  test('New password and confirmation password do not match', async ({
    page,
  }) => {
    await page.getByTestId('current-password-input').fill(password)
    await page.getByTestId('new-password-input').fill(randomPassword())
    await page.getByTestId('confirm-password-input').fill(randomPassword())
    await page.getByRole('button', { name: 'Update password' }).click()

    await expect(page.getByText("The passwords don't match")).toBeVisible()
  })

  test('Current password and new password are the same', async ({ page }) => {
    await page.getByTestId('current-password-input').fill(password)
    await page.getByTestId('new-password-input').fill(password)
    await page.getByTestId('confirm-password-input').fill(password)
    await page.getByRole('button', { name: 'Update password' }).click()

    await expect(
      page.getByText('New password cannot be the same as the current one'),
    ).toBeVisible()
  })
})

test('Appearance options are reachable from the profile menu', async ({
  page,
}) => {
  await page.goto('/settings')

  await page.getByRole('button', { name: 'Open profile menu' }).click()
  await page.getByRole('menuitem', { name: 'Appearance' }).click()

  for (const label of ['System Default', 'Light', 'Dark']) {
    await expect(
      page.getByRole('menuitem', { name: label, exact: true }),
    ).toBeVisible()
  }
})

test('User can switch between theme modes', async ({ page }) => {
  await page.goto('/settings')

  await selectTheme(page, 'Dark')
  await expect(page.locator('html')).toHaveClass(/dark/)

  await selectTheme(page, 'Light')
  await expect(page.locator('html')).toHaveClass(/light/)
})

test('Selected mode is preserved across sessions', async ({ page }) => {
  await page.goto('/settings')

  await selectTheme(page, 'Light')
  await expect(page.locator('html')).toHaveClass(/light/)

  await selectTheme(page, 'Dark')
  await expect(page.locator('html')).toHaveClass(/dark/)

  await logOutUser(page)
  await logInUser(page, firstSuperuser, firstSuperuserPassword)

  await expect(page.locator('html')).toHaveClass(/dark/)
})
