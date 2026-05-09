import { useInfiniteQuery } from '@tanstack/react-query'
import { useCallback, useRef } from 'react'

import { type ArticlesPublic, ArticlesService } from '@/client'
import { isLoggedIn } from '@/lib/auth-state'
import { ARTICLES_PAGE_SIZE } from '@/lib/constants'

const FOLLOWING_FEED_STALE_TIME_MS = 1000 * 30

/**
 * Followed-sources feed driver. Same shape as useArticleFeed so the
 * route component can drop it into the same ArticleList without
 * branching. Sorting and filtering live entirely on the backend
 * (`/articles/following`); this hook only paginates.
 *
 * Auth-gated like useForYouFeed — disabled for anonymous visitors so a
 * logged-out tab switch can't hit a 401. The Following tab is hidden
 * for guests at the route level too, so this is a defense-in-depth
 * guard rather than the primary control.
 */
export function useFollowingFeed() {
  const observerRef = useRef<IntersectionObserver | null>(null)

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isError,
    isPending,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['followingFeed'],
    initialPageParam: 0,
    queryFn: ({ pageParam }: { pageParam: number }) =>
      ArticlesService.readFollowing({
        skip: pageParam,
        limit: ARTICLES_PAGE_SIZE,
      }),
    getNextPageParam: (
      lastPage: ArticlesPublic,
      allPages: ArticlesPublic[],
    ) => {
      const loaded = allPages.reduce(
        (total, page) => total + page.data.length,
        0,
      )
      return loaded < lastPage.count ? loaded : undefined
    },
    enabled: isLoggedIn(),
    staleTime: FOLLOWING_FEED_STALE_TIME_MS,
  })

  const articles = data?.pages.flatMap((page) => page.data) ?? []

  const feedStatus = isFetchingNextPage
    ? 'Loading more...'
    : !hasNextPage && articles.length > 0
      ? "You're all caught up."
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
