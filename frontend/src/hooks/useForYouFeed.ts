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
}

const fetchPage = async (skip: number): Promise<ForYouPage> => {
  return ArticlesService.readForYou({
    skip,
    limit: ARTICLES_PAGE_SIZE,
  })
}

/**
 * Personalized feed driver. Same shape as useArticleFeed so the route
 * component can drop in either interchangeably. Pagination is over the
 * scored output (see services/for_you.py) — once we've shown all the
 * ranked candidates, hasNextPage becomes false even if more recent
 * articles exist that didn't make the candidate pool.
 */
export function useForYouFeed() {
  const observerRef = useRef<IntersectionObserver | null>(null)

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isError,
    isPending,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['forYouFeed'],
    initialPageParam: 0,
    queryFn: ({ pageParam }: { pageParam: number }) => fetchPage(pageParam),
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

  return { articles, feedStatus, loadMoreRef, isPending, isError }
}
