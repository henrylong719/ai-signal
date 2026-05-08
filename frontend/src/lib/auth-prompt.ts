export const ARTICLE_FEED_LOAD_MORE_EVENT = 'ai-signal:article-feed-load-more'

export function notifyArticleFeedLoadMore() {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(ARTICLE_FEED_LOAD_MORE_EVENT))
}
