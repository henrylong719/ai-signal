import { useInfiniteQuery } from '@tanstack/react-query'
import { useCallback, useRef } from 'react'

import { ArticlesService, type ForYouArticlePublic } from '@/client'
import { isLoggedIn } from '@/lib/auth-state'
import { ARTICLES_PAGE_SIZE } from '@/lib/constants'

const FOR_YOU_FEED_STALE_TIME_MS = 1000 * 30

export type ForYouArticle = ForYouArticlePublic

interface ForYouPage {
  data: ForYouArticle[]
  count: number
  candidate_pool_cap: number
  // Surfaced only when the request asks for debug AND the caller is a
  // superuser. Always undefined on normal responses.
  weights?: {
    semantic: number
    explicit: number
    source: number
    recency: number
  } | null
}

const fetchPage = async (skip: number, debug: boolean): Promise<ForYouPage> => {
  return ArticlesService.readForYou({
    skip,
    limit: ARTICLES_PAGE_SIZE,
    // The generated client picks up `debug` after OpenAPI codegen runs.
    // Until then this property is ignored at the TS level and
    // forwarded as a query string by the underlying fetch call.
    ...(debug ? { debug: true } : {}),
  } as Parameters<typeof ArticlesService.readForYou>[0])
}

/**
 * Personalized feed driver. Same shape as useArticleFeed so the route
 * component can drop in either interchangeably. Pagination is over the
 * scored output (see services/for_you.py) — once we've shown all the
 * ranked candidates, hasNextPage becomes false even if more recent
 * articles exist that didn't make the candidate pool.
 *
 * The optional ``debug`` flag asks the backend for the per-article
 * scoring breakdown and exploration-injection flags. Backend silently
 * ignores it for non-superusers, so passing it from the route is safe;
 * the panel just won't render anything for regular users. The query
 * key includes ``debug`` so toggling it from the URL refetches rather
 * than reusing the no-debug cache.
 */
export function useForYouFeed(opts: { debug?: boolean } = {}) {
  const debug = !!opts.debug
  const observerRef = useRef<IntersectionObserver | null>(null)

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isError,
    isPending,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['forYouFeed', { debug }],
    initialPageParam: 0,
    queryFn: ({ pageParam }: { pageParam: number }) =>
      fetchPage(pageParam, debug),
    getNextPageParam: (lastPage: ForYouPage, allPages: ForYouPage[]) => {
      const loaded = allPages.reduce(
        (total, page) => total + page.data.length,
        0,
      )
      return loaded < lastPage.count ? loaded : undefined
    },
    // Don't request the personalized feed for anonymous visitors —
    // it would 401 and bounce them through the login flow even though
    // they were just browsing.
    enabled: isLoggedIn(),
    staleTime: FOR_YOU_FEED_STALE_TIME_MS,
  })

  const articles: ForYouArticle[] =
    data?.pages.flatMap((page) => page.data) ?? []
  const lastPage = data?.pages[data.pages.length - 1]
  const exhaustedCandidatePool =
    lastPage !== undefined && lastPage.count >= lastPage.candidate_pool_cap

  const feedStatus = isFetchingNextPage
    ? 'Loading more...'
    : !hasNextPage && articles.length > 0
      ? exhaustedCandidatePool
        ? "That's all your top picks for now."
        : "You're all caught up."
      : !hasNextPage
        ? 'Your personalized feed is empty for now.'
        : null

  const loadMoreRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (observerRef.current) {
        observerRef.current.disconnect()
        observerRef.current = null
      }
      if (!node || !hasNextPage) return
      observerRef.current = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting && !isFetchingNextPage) {
            void fetchNextPage()
          }
        },
        { rootMargin: '300px' },
      )
      observerRef.current.observe(node)
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage],
  )

  // The active scoring weights from the latest page. Surfaced only on
  // debug responses; consumers that aren't in debug mode get undefined.
  const weights = lastPage?.weights ?? null

  return { articles, feedStatus, loadMoreRef, isPending, isError, weights }
}
