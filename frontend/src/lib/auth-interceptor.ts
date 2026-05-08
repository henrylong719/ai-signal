import axios, { type AxiosRequestConfig, type AxiosResponse } from 'axios'

import { OpenAPI } from '@/client'

/**
 * 401-on-API → refresh-and-retry interceptor.
 *
 * The frontend never holds the access token directly (it lives in an
 * httpOnly cookie). When the token expires server-side, the next API
 * call returns 401. This interceptor catches that, calls the refresh
 * endpoint (which uses the long-lived refresh cookie to mint new
 * access cookies), and retries the original request.
 *
 * Three subtleties handled here:
 *
 * 1. Promise singleton. If ten parallel requests all 401 at once
 *    (typical when many React Query queries are in-flight), only one
 *    refresh runs — the rest await the same in-flight promise. Without
 *    this, we'd hammer the refresh endpoint and potentially confuse
 *    refresh-token rotation.
 *
 * 2. No-loop guard. We never refresh on the refresh endpoint itself,
 *    and we never retry a request more than once. Both of these are
 *    necessary to avoid refresh→401→refresh death spirals when the
 *    refresh token itself is invalid.
 *
 * 3. Refresh failure → user is logged out. If refresh returns non-2xx,
 *    we clear the marker cookie and redirect to login. The actual auth
 *    cookies have already been cleared server-side as part of the
 *    failure response (or were never valid to begin with).
 */

const REFRESH_PATH = '/api/v1/login/refresh'
const LOGIN_PATH = '/login'

/**
 * In-flight refresh promise. While set, all 401-handlers await this
 * instead of starting a new refresh. Cleared when the refresh resolves
 * (success or failure) so the next 401 can start a fresh attempt.
 */
let refreshInFlight: Promise<boolean> | null = null

/**
 * Request configs that have already been retried once and shouldn't be
 * retried again. Tracked by a Symbol stamped onto the config so we can
 * recognize it in the interceptor without leaking state across requests.
 */
const RETRIED = Symbol('RETRIED_AFTER_REFRESH')

interface RetryableConfig extends AxiosRequestConfig {
  [RETRIED]?: boolean
}

const refreshSession = async (): Promise<boolean> => {
  // Use a bare axios call rather than the SDK's LoginService.refreshSession.
  // The SDK call would itself go through this interceptor, which is fine,
  // but using bare axios keeps the interceptor logic obviously self-contained
  // and avoids any chance of an SDK-layer transformation interfering with
  // the cookie round-trip.
  try {
    const response = await axios.post(
      `${OpenAPI.BASE}${REFRESH_PATH}`,
      undefined,
      { withCredentials: true },
    )
    return response.status >= 200 && response.status < 300
  } catch {
    return false
  }
}

const onRefreshFailure = () => {
  // Mark the user logged-out client-side. The backend already cleared the
  // server cookies in its 401 response (or never set valid ones). The
  // marker cookie is the SPA's UI-state hint; clearing it here keeps the
  // sidebar from flashing "logged in" briefly after a hard refresh.
  // biome-ignore lint/suspicious/noDocumentCookie: Cookie Store API lacks broad support for expiry; document.cookie is required here
  document.cookie = 'is_logged_in=; Max-Age=0; Path=/; SameSite=Lax'
  // Hard navigate so React Query caches, in-memory state, and any other
  // user-tied state are reset. A soft navigate via the router would
  // leave stale data behind.
  if (
    typeof window !== 'undefined' &&
    !window.location.pathname.startsWith(LOGIN_PATH)
  ) {
    window.location.href = LOGIN_PATH
  }
}

/**
 * Response interceptor entry point. Wired up in main.tsx via
 * OpenAPI.interceptors.response.use(authInterceptor).
 */
export const authInterceptor = async (
  response: AxiosResponse,
): Promise<AxiosResponse> => {
  // Only react to 401. Other failures aren't auth-related.
  if (response.status !== 401) return response

  const config = response.config as RetryableConfig | undefined
  if (!config) return response

  // Don't try to refresh on the refresh endpoint itself — that's the
  // signal that the refresh token is also dead.
  if (config.url?.endsWith(REFRESH_PATH)) {
    onRefreshFailure()
    return response
  }

  // Don't retry a request we've already retried once.
  if (config[RETRIED]) return response

  // Coalesce concurrent refreshes into one.
  refreshInFlight ??= refreshSession().finally(() => {
    refreshInFlight = null
  })
  const refreshed = await refreshInFlight

  if (!refreshed) {
    onRefreshFailure()
    return response
  }

  // Refresh succeeded. The browser now has a fresh access cookie.
  // Replay the original request and return its response in place of
  // the 401. The interceptor doesn't run on the replay because
  // axios.request() bypasses the OpenAPI client interceptor chain
  // — that's fine, a properly refreshed request shouldn't 401 again,
  // and even if it did, RETRIED prevents looping.
  config[RETRIED] = true
  return await axios.request(config)
}
