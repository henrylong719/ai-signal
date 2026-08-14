import type { Page } from '@playwright/test'

/**
 * Reveal the email/password form on /login and /signup.
 *
 * Both routes render AuthFlow, which opens on a provider chooser
 * (Google / GitHub / Facebook / email). The email fields are not mounted
 * until "Continue with email" is clicked, so every test that types into
 * them has to come through here first.
 *
 * Kept in one place because the specs and the shared user helpers had
 * drifted apart: login.spec.ts and sign-up.spec.ts each grew their own
 * copy when the provider step was added, while auth.setup.ts and
 * utils/user.ts were never updated and silently broke the whole suite.
 */
export async function openEmailAuthForm(page: Page) {
  await page.getByRole('button', { name: 'Continue with email' }).click()
}
