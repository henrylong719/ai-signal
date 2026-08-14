import type { Page } from '@playwright/test'

const ONBOARDING_PATH = '/api/v1/users/me/onboarding'

/**
 * Mark the signed-in user's first-run onboarding complete, then reload.
 *
 * AppShell renders OnboardingDialog, which opens a modal for any user
 * whose `onboarded_at` is null. Test users are created fresh, so that is
 * every one of them: the modal covers the app, puts the background under
 * aria-hidden, and every `getByRole` in the suite stops matching.
 *
 * Dismissing it by clicking "Skip for now" would mean probing for a
 * dialog that may or may not have mounted yet — a race. Setting the flag
 * server-side and reloading is deterministic: the reload drops the React
 * Query cache, the refetched user has `onboarded_at` set, and the modal
 * never opens.
 *
 * Relative path on purpose — `page.request` shares the browser context's
 * cookie jar and baseURL, so this call is authenticated the same way the
 * app's own requests are.
 */
export async function completeOnboarding(page: Page) {
  const response = await page.request.put(ONBOARDING_PATH, { data: {} })
  if (!response.ok()) {
    throw new Error(
      `Failed to complete onboarding: ${response.status()} ${response.statusText()}`,
    )
  }
  await page.reload()
}
