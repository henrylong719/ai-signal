import type { APIRequestContext } from '@playwright/test'
import { firstSuperuser, firstSuperuserPassword } from '../config.ts'

const apiBase = process.env.PLAYWRIGHT_API_URL ?? process.env.VITE_API_URL ?? ''

/**
 * Fetch the password-recovery email HTML for a user, reset link included.
 *
 * Why not read the actual email? Transactional mail moved from SMTP to
 * Resend's HTTP API (see app/services/resend_email.py), so nothing is
 * delivered to the mailcatcher container any more and the old
 * findLastEmail() poll just times out. Resend has no local sandbox in
 * this stack and its endpoint is a module constant, so there is nothing
 * to point at a stub either.
 *
 * `POST /login/password-recovery-html-content/{email}` renders that exact
 * email — same template, same freshly generated token — for superusers.
 * Sourcing the link from there keeps the meaningful half of the test (the
 * token actually works and the reset flow completes) and drops only the
 * delivery hop, which this stack can no longer exercise.
 *
 * Node-side, so it addresses the backend container directly and carries a
 * bearer token rather than relying on the browser's cookie jar.
 */
export async function fetchRecoveryEmailHtml(
  request: APIRequestContext,
  email: string,
): Promise<string> {
  // No /login prefix on the router — each route spells its own path, so
  // it is /api/v1/login/access-token but /api/v1/password-recovery-*.
  const loginResponse = await request.post(
    `${apiBase}/api/v1/login/access-token`,
    {
      form: {
        username: firstSuperuser,
        password: firstSuperuserPassword,
      },
    },
  )
  if (!loginResponse.ok()) {
    throw new Error(
      `Superuser login failed: ${loginResponse.status()} ${loginResponse.statusText()}`,
    )
  }
  const { access_token: accessToken } = await loginResponse.json()

  const response = await request.post(
    `${apiBase}/api/v1/password-recovery-html-content/${encodeURIComponent(email)}`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  )
  if (!response.ok()) {
    throw new Error(
      `Could not render recovery email for ${email}: ${response.status()} ${response.statusText()}`,
    )
  }
  return response.text()
}

/**
 * Pull the /reset-password?token=... link out of the recovery email and
 * return it as a path, ready for page.goto() against the app's baseURL.
 */
export function extractResetPasswordPath(html: string): string {
  const match = html.match(/href="[^"]*(\/reset-password\?token=[^"&]+)"/)
  if (!match) {
    throw new Error('No reset-password link found in the recovery email')
  }
  return match[1].replace(/&amp;/g, '&')
}
