import { useQuery } from '@tanstack/react-query'

import { ArticlesService, type SourcesPublic } from '@/client'

const SOURCES_KEY = ['articleSources'] as const

// Sources rarely change at runtime — once an hour is plenty fresh.
// Long staleTime + matching gcTime means navigating to and from the
// personalization page in one session reuses the cached list.
const ONE_HOUR_MS = 1000 * 60 * 60

/**
 * Read the canonical list of article sources from the backend.
 *
 * Uses the existing `GET /api/v1/articles/sources/` endpoint as the
 * single source of truth — never hardcode a parallel list on the
 * frontend. If the backend adds a source, this picker picks it up
 * automatically; if it removes one, the picker stops offering it.
 *
 * The query is not auth-gated: source listings are public, and the
 * personalization page renders the auth gate at the route level.
 */
export function useSources() {
  const { data, isLoading, isError } = useQuery<SourcesPublic, Error>({
    queryKey: SOURCES_KEY,
    queryFn: () => ArticlesService.readSources(),
    staleTime: ONE_HOUR_MS,
    gcTime: ONE_HOUR_MS,
  })

  return {
    sources: data?.data ?? [],
    isLoading,
    isError,
  }
}
