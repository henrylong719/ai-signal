import { OpenAPI } from "@/client"

/**
 * URL the article card links to instead of the external URL.
 *
 * Hitting this endpoint records a click event for the user (when signed
 * in — clicks from anonymous visitors are not logged) and then 302s to
 * the article's real URL. The user experience is unchanged from a direct
 * link — the redirect adds maybe 50ms.
 *
 * Cookie auth is what makes this work: a plain ``<a href>`` navigation
 * does not run JavaScript, so a Bearer token in localStorage would be
 * lost. The browser includes the access cookie automatically.
 *
 * If we ever want UTM tagging on outbound clicks, this is the one place
 * to add it.
 */
export const redirectHref = (articleId: string): string => {
  return `${OpenAPI.BASE}/api/v1/articles/${articleId}/go`
}
