/**
 * First-party anonymous analytics for the guest funnel.
 *
 * Tiny by design:
 *
 *  - One ID kept in localStorage. No cookies, no fingerprinting, no
 *    third-party SDKs.
 *  - Events are posted to our own backend via the auto-generated client
 *    and treated as best-effort: failures must never break UI flows.
 *  - Logged-in users are skipped by default (see ``trackGuestEvent``);
 *    the only event that crosses the auth boundary is
 *    ``guest_signup_completed``, which links the anonymous_id to the
 *    new user_id.
 *
 * If localStorage is unavailable (private mode, storage disabled), we
 * generate a per-tab id and just don't persist it — analytics is best
 * effort, and zero traffic from that browser is preferable to a hard
 * error.
 */

import type { GuestEventCreate } from '@/client'
import { AnalyticsService } from '@/client'
import { isLoggedIn } from '@/lib/auth-state'

const ANONYMOUS_ID_KEY = 'ai_signal_anonymous_id'

type EventType = GuestEventCreate['event_type']

let cachedAnonymousId: string | null = null

const isBrowser = (): boolean =>
  typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'

const generateUuid = (): string => {
  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return crypto.randomUUID()
  }
  // Fallback for very old browsers / SSR. Not cryptographically random
  // — but the anonymous id is not a security token, just a stable
  // browser identifier for funnel analytics.
  return `anon-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

export const getAnonymousId = (): string => {
  if (cachedAnonymousId) return cachedAnonymousId

  if (!isBrowser()) {
    // SSR or test envs without window. Return a throwaway id; the page
    // mount will re-evaluate once we're in the browser.
    cachedAnonymousId = generateUuid()
    return cachedAnonymousId
  }

  try {
    const existing = window.localStorage.getItem(ANONYMOUS_ID_KEY)
    if (existing && existing.length > 0 && existing.length <= 64) {
      cachedAnonymousId = existing
      return existing
    }
  } catch {
    // localStorage may throw in private mode or when blocked by the
    // user's settings. Fall through to in-memory id below.
  }

  const fresh = generateUuid()
  try {
    window.localStorage.setItem(ANONYMOUS_ID_KEY, fresh)
  } catch {
    // Same as above — non-fatal. The id stays in memory for this tab.
  }
  cachedAnonymousId = fresh
  return fresh
}

interface TrackOptions {
  /**
   * Force-send the event even when ``isLoggedIn()`` returns true.
   * Used for ``guest_signup_completed`` which fires *after* the user
   * is authenticated.
   */
  forceWhenLoggedIn?: boolean
  /**
   * Extra payload merged into the request. Keep it small — the backend
   * enforces a hard cap on ``metadata``.
   */
  payload?: Omit<Partial<GuestEventCreate>, 'anonymous_id' | 'event_type'>
}

const safePath = (): string | undefined => {
  if (typeof window === 'undefined') return undefined
  try {
    return window.location.pathname + (window.location.search ?? '')
  } catch {
    return undefined
  }
}

const safeReferrer = (): string | undefined => {
  if (typeof document === 'undefined') return undefined
  try {
    return document.referrer || undefined
  } catch {
    return undefined
  }
}

/**
 * Fire-and-forget analytics call. Returns nothing. Logs to the
 * console only at the debug level so noisy DevTools sessions don't get
 * cluttered.
 */
export const trackGuestEvent = (
  eventType: EventType,
  options: TrackOptions = {},
): void => {
  // The guest funnel is, by definition, about logged-out users. The
  // single exception is the signup-completion event, which the caller
  // must opt in to via ``forceWhenLoggedIn``.
  if (isLoggedIn() && !options.forceWhenLoggedIn) {
    return
  }

  const body: GuestEventCreate = {
    anonymous_id: getAnonymousId(),
    event_type: eventType,
    path: options.payload?.path ?? safePath() ?? null,
    ...(options.payload ?? {}),
  }

  // ``referrer`` is only meaningful on first paint — attach it lazily
  // so callers don't have to think about it for non-page-view events.
  if (eventType === 'guest_page_view' && body.referrer == null) {
    const ref = safeReferrer()
    if (ref) {
      body.referrer = ref
    }
  }

  // The SDK uses axios; let the call resolve in the background. We
  // swallow rejections silently per the privacy/UX contract.
  AnalyticsService.recordGuestEvent({ requestBody: body }).catch(() => {
    // Intentionally empty — analytics is best-effort.
  })
}

/**
 * Test-only escape hatch to drop the in-memory id cache so unit tests
 * (or hot-module-reload sessions) can simulate a fresh visitor without
 * touching localStorage manually.
 */
export const resetAnonymousIdForTests = (): void => {
  cachedAnonymousId = null
}
