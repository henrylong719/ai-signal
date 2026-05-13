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
 * Four subtleties handled here:
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
 * 3. Distinguish auth failure from transient failure. A 401/403 from
 *    the refresh endpoint means the server rejected the refresh token
 *    — log the user out. A network error, timeout, or 5xx means the
 *    refresh never actually completed — retry once with backoff, and
 *    if it's still transient, leave the user logged in so the next
 *    request can try again. Conflating these two cases is what kicks
 *    users off on flaky mobile networks.
 *
 * 4. Refresh failure → user is logged out. If refresh definitively
 *    fails (server-rejected), we clear the marker cookie and redirect
 *    to login. The actual auth cookies have already been cleared
 *    server-side as part of the failure response.
 */

const REFRESH_PATH = '/api/v1/login/refresh'
const LOGIN_PATH = '/login'
const TRANSIENT_RETRY_DELAY_MS = 800

type RefreshResult = 'ok' | 'auth_failed' | 'transient'

/**
 * In-flight refresh promise. While set, all 401-handlers await this
 * instead of starting a new refresh. Cleared when the refresh resolves
 * (success or failure) so the next 401 can start a fresh attempt.
 */
let refreshInFlight: Promise<RefreshResult> | null = null

/**
 * Request configs that have already been retried once and shouldn't be
 * retried again. Tracked by a Symbol stamped onto the config so we can
 * recognize it in the interceptor without leaking state across requests.
 */
const RETRIED = Symbol('RETRIED_AFTER_REFRESH')

interface RetryableConfig extends AxiosRequestConfig {
  [RETRIED]?: boolean
}

const attemptRefresh = async (): Promise<RefreshResult> => {
  // Use a bare axios call rather than the SDK's LoginService.refreshSession.
  // The SDK call would itself go through this interceptor, which is fine,
  // but using bare axios keeps the interceptor logic obviously self-contained
  // and avoids any chance of an SDK-layer transformation interfering with
  // the cookie round-trip.
  //
  // ``validateStatus: () => true`` keeps axios from throwing on any HTTP
  // status, so we can branch on the status code directly. Anything thrown
  // here is therefore a network-level error (no response, timeout, DNS,
  // CORS-preflight failure), which we treat as transient.
  try {
    const response = await axios.post(
      `${OpenAPI.BASE}${REFRESH_PATH}`,
      undefined,
      { withCredentials: true, validateStatus: () => true },
    )
    if (response.status >= 200 && response.status < 300) return 'ok'
    // 401/403 = server actively rejected the refresh token. Anything else
    // (5xx, 502 from a Railway cold start, 404 from a misrouted proxy, etc.)
    // is not an auth signal — don't log the user out for it.
    if (response.status === 401 || response.status === 403) return 'auth_failed'
    return 'transient'
  } catch {
    return 'transient'
  }
}

const refreshSession = async (): Promise<RefreshResult> => {
  // Retry once on transient errors. Mobile networks often drop the first
  // packet after a tab resumes from background; a single retry with a
  // short backoff is the cheapest way to avoid kicking the user out.
  const first = await attemptRefresh()
  if (first !== 'transient') return first
  await new Promise((resolve) => setTimeout(resolve, TRANSIENT_RETRY_DELAY_MS))
  return attemptRefresh()
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
  const result = await refreshInFlight

  if (result === 'auth_failed') {
    onRefreshFailure()
    return response
  }

  if (result === 'transient') {
    // Network/5xx during refresh — leave the user logged in. Return the
    // original 401 so the caller sees the failure; the next API call
    // will start another refresh attempt once the network recovers.
    return response
  }

  // Refresh succeeded. The browser now has a fresh access cookie.
  // Replay the original request and return its response in place of
  // the 401. The interceptor doesn't run on the replay because
  // axios.request() bypasses the OpenAPI client interceptor chain
  // — that's fine, a properly refreshed request shouldn't 401 again,
  // and even if it did, RETRIED prevents looping.
  config[RETRIED] = true
  const retried = await axios.request(config)
  // If the retried request still comes back 401 (e.g., user was
  // deactivated between the refresh and the retry), treat that as a
  // definitive auth failure here — otherwise nothing would redirect.
  if (retried.status === 401) {
    onRefreshFailure()
  }
  return retried
}
