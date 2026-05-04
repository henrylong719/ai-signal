import { useInfiniteQuery } from "@tanstack/react-query"
import { useCallback, useRef } from "react"
import { type ArticlesPublic, ArticlesService, type category } from "@/client"
import { ARTICLES_PAGE_SIZE } from "@/lib/constants"

interface UseArticleFeedOptions {
  category?: category
  search?: string
  source?: string
}

export function useArticleFeed(options: UseArticleFeedOptions = {}) {
  const observerRef = useRef<IntersectionObserver | null>(null)

  const queryOptions = {
    queryKey: [
      "articles",
      options.category ?? null,
      options.search ?? null,
      options.source ?? null,
    ],
    initialPageParam: 0,
    queryFn: ({ pageParam }: { pageParam: number }) =>
      ArticlesService.readArticles({
        skip: pageParam,
        limit: ARTICLES_PAGE_SIZE,
        ...(options.category && { category: options.category }),
        ...(options.search && { search: options.search }),
        ...(options.source && { source: options.source }),
      }),
    getNextPageParam: (
      lastPage: ArticlesPublic,
      allPages: ArticlesPublic[],
    ) => {
      const loadedArticles = allPages.reduce(
        (total, page) => total + page.data.length,
        0,
      )
      return loadedArticles < lastPage.count ? loadedArticles : undefined
    },
  }

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isError,
    isPending,
    isFetchingNextPage,
  } = useInfiniteQuery(queryOptions)

  const articles = data?.pages.flatMap((page) => page.data) ?? []

  const feedStatus = isFetchingNextPage
    ? "Loading more..."
    : !hasNextPage && articles.length > 0
      ? "You're all caught up."
      : !hasNextPage
        ? "No articles yet."
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
        { rootMargin: "300px" },
      )

      observerRef.current.observe(node)
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage],
  )

  return { articles, feedStatus, loadMoreRef, isPending, isError }
}
