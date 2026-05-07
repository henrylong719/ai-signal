import { useInfiniteQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useCallback, useRef } from 'react'

import { type ArticlePublic, OpenAPI } from '@/client'
import { isLoggedIn } from '@/lib/auth-state'
import { ARTICLES_PAGE_SIZE } from '@/lib/constants'

/**
 * Wire shape of GET /articles/for-you. Mirrors ForYouArticlesPublic on
 * the backend. Defined locally because the OpenAPI client hasn't been
 * regenerated against the updated backend yet.
 *
 * TODO: replace with the generated ArticlesService types after running
 *   `npm run generate-client` and use ArticlesService.readForYou.
 */
export interface ForYouArticle extends ArticlePublic {
  reason: string | null
}

interface ForYouPage {
  data: ForYouArticle[]
  count: number
}

const FOR_YOU_PATH = '/api/v1/articles/for-you'

const fetchPage = async (skip: number): Promise<ForYouPage> => {
  const r = await axios.get<ForYouPage>(`${OpenAPI.BASE}${FOR_YOU_PATH}`, {
    params: { skip, limit: ARTICLES_PAGE_SIZE },
    withCredentials: true,
  })
  return r.data
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
  })

  const articles: ForYouArticle[] =
    data?.pages.flatMap((page) => page.data) ?? []

  const feedStatus = isFetchingNextPage
    ? 'Loading more...'
    : !hasNextPage && articles.length > 0
      ? "You're all caught up."
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
