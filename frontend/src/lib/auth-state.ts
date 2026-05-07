/**
 * Login-state helpers backed by the non-httpOnly marker cookie.
 *
 * The actual access and refresh tokens live in httpOnly cookies that
 * JavaScript cannot read. This module reads only the `is_logged_in`
 * marker cookie, which is purely a UI hint — the server never trusts
 * it for authorization.
 *
 * Why a marker cookie at all? Because the alternative is a /users/me
 * probe on every page load before any UI can render, which costs a
 * round-trip and a loading state. The marker lets the SPA render its
 * login state on first paint.
 */

const MARKER_COOKIE_NAME = 'is_logged_in'

/**
 * Read the marker cookie. Synchronous, no network. Returns false when
 * the cookie isn't set, has been cleared, or contains anything other
 * than the canonical "1" value.
 *
 * SECURITY: This is a UI hint only. NEVER use it to gate access to
 * sensitive operations — only the server's auth check on the actual
 * httpOnly access cookie is trustworthy.
 */
export const isLoggedIn = (): boolean => {
  if (typeof document === 'undefined') return false
  for (const part of document.cookie.split(';')) {
    const [name, value] = part.trim().split('=')
    if (name === MARKER_COOKIE_NAME && value === '1') return true
  }
  return false
}

/**
 * Clear the marker cookie locally. Used after a refresh failure to
 * stop the SPA from showing logged-in UI before a hard navigate to
 * /login. The httpOnly auth cookies are cleared by the server; this
 * function only handles the JS-readable marker.
 */
export const clearLoginState = (): void => {
  if (typeof document === 'undefined') return
  document.cookie = `${MARKER_COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax`
}
