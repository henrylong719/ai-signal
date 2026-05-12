import { createFileRoute, Outlet, useLocation } from '@tanstack/react-router'
import { AlertCircleIcon, BookmarkIcon, SearchIcon, XIcon } from 'lucide-react'
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { SourcePublic, source_type } from '@/client'
import { ArticleListState } from '@/components/Articles/ArticleList'
import { PageContainer, PageHeader } from '@/components/Layout/Page'
import SourceFilterBar from '@/components/Source/SourceFilterBar'
import SourceGroupSkeleton from '@/components/Source/SourceGroupSkeleton'
import SourceSection from '@/components/Source/SourceSection'
import { useInterests } from '@/hooks/useInterests'
import { useSources } from '@/hooks/useSources'
import { isLoggedIn } from '@/lib/auth-state'
import {
  SOURCE_FILTER_LABELS,
  SOURCE_TYPES,
  type source_types,
} from '@/lib/constants'
import { buildPageMeta } from '@/lib/meta'

export const Route = createFileRoute('/_layout/all-article-sources')({
  component: AllArticleSources,
  head: () =>
    buildPageMeta({
      title: 'All article sources',
      description:
        'Browse every source behind AI Signal — labs, research feeds, analysis, policy groups, media outlets, newsletters, podcasts, and community sites.',
      path: '/all-article-sources',
    }),
})

const isSourceType = (value: unknown): value is source_types =>
  typeof value === 'string' && SOURCE_TYPES.includes(value as source_types)

type SearchableSource = SourcePublic & {
  category?: string
  domain?: string
  tags?: string[]
  type?: string
  url?: string
  website_url?: string
}

const getSourceSearchText = (source: SourcePublic) => {
  const searchableSource = source as SearchableSource

  return [
    source.name,
    source.description,
    source.default_category,
    source.source_type,
    source.topic,
    SOURCE_FILTER_LABELS[source.source_type as keyof typeof SOURCE_FILTER_LABELS],
    searchableSource.category,
    searchableSource.domain,
    searchableSource.type,
    searchableSource.url,
    searchableSource.website_url,
    ...(searchableSource.tags ?? []),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
}

/** Normalizes user query: lowercase, treat `-` `/` `_` as word breaks, single spaces. */
const normalizeSourceSearchQuery = (raw: string) =>
  raw
    .trim()
    .toLowerCase()
    .replace(/[-_/]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

/**
 * True if the source matches the search query.
 * - Full phrase substring match (existing behavior).
 * - Otherwise, every whitespace-separated token must appear as a substring in the haystack
 *   (e.g. "deep learning" matches "DeepLearningAI" because both "deep" and "learning" appear).
 */
const sourceMatchesSearchQuery = (source: SourcePublic, normalizedQuery: string) => {
  if (!normalizedQuery) return true

  const haystack = getSourceSearchText(source)
  if (haystack.includes(normalizedQuery)) return true

  const tokens = normalizedQuery.split(' ').filter(Boolean)
  if (tokens.length <= 1) return false

  return tokens.every((token) => haystack.includes(token))
}

function AllArticleSources() {
  const location = useLocation()
  const savedRouteState = location.state as {
    allArticleSourcesFilter?: unknown
    allArticleSourcesScrollY?: unknown
  }
  const userIsLoggedIn = isLoggedIn()
  const [sourceFilter, setSourceFilter] = useState<source_types>(() => {
    const saved = savedRouteState.allArticleSourcesFilter
    if (!isSourceType(saved)) return 'all'
    if (saved === 'following' && !userIsLoggedIn) return 'all'
    return saved
  })
  const [sourceQuery, setSourceQuery] = useState('')
  const [updatingSource, setUpdatingSource] = useState<string | null>(null)
  const hasRestoredScroll = useRef(false)

  const { sources, isLoading, isError } = useSources()
  const {
    interests,
    isLoading: interestsLoading,
    isError: interestsError,
    save,
    isSaving,
  } = useInterests()

  const savedScrollY = savedRouteState.allArticleSourcesScrollY

  useLayoutEffect(() => {
    if (
      hasRestoredScroll.current ||
      isLoading ||
      typeof savedScrollY !== 'number'
    ) {
      return
    }

    hasRestoredScroll.current = true
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: savedScrollY })
    })
  }, [isLoading, savedScrollY])

  const preferredSources = interests?.preferred_sources ?? []
  const followDisabled = interestsLoading || interestsError || isSaving

  const filterTypes = useMemo<source_types[]>(
    () =>
      userIsLoggedIn
        ? SOURCE_TYPES
        : SOURCE_TYPES.filter((type) => type !== 'following'),
    [userIsLoggedIn],
  )

  const followedSources = useMemo(
    () => sources.filter((source) => preferredSources.includes(source.name)),
    [sources, preferredSources],
  )

  const normalizedSourceQuery = normalizeSourceSearchQuery(sourceQuery)

  const filteredSources =
    sourceFilter === 'all'
      ? sources
      : sourceFilter === 'following'
        ? followedSources
        : sources.filter((source) => source.source_type === sourceFilter)

  const visibleSources = normalizedSourceQuery
    ? filteredSources.filter((source) =>
        sourceMatchesSearchQuery(source, normalizedSourceQuery),
      )
    : filteredSources

  const groups: Array<{
    type: Exclude<source_types, 'all'>
    items: typeof sources
  }> =
    sourceFilter === 'following'
      ? visibleSources.length > 0
        ? [{ type: 'following', items: visibleSources }]
        : []
      : SOURCE_TYPES.filter(
          (type): type is source_type => type !== 'all' && type !== 'following',
        )
          .map((type) => ({
            type,
            items: visibleSources.filter(
              (source) => source.source_type === type,
            ),
          }))
          .filter((group) => group.items.length > 0)

  const togglePreferredSource = (sourceName: string) => {
    if (!userIsLoggedIn || interestsLoading || interestsError) {
      return
    }

    const isRemovingSource = preferredSources.includes(sourceName)
    const nextPreferredSources = isRemovingSource
      ? preferredSources.filter((source) => source !== sourceName)
      : [...preferredSources, sourceName]

    setUpdatingSource(sourceName)
    save(
      {
        categories: interests?.categories ?? [],
        tags: interests?.tags ?? [],
        preferred_sources: nextPreferredSources,
      },
      {
        successMessage: isRemovingSource
          ? `${sourceName} removed from your followed sources.`
          : `You're now following ${sourceName}.`,
        onSettled: () => setUpdatingSource(null),
      },
    )
  }

  return (
    <PageContainer variant="default">
      <PageHeader
        eyebrow="Directory"
        title="Sources"
        description="Explore the labs, research feeds, analysis, policy groups, media outlets, newsletters, podcasts, and community sites behind AI Signal."
      />

      <div className="mb-4">
        <div className="group/source-search relative">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 transition-colors group-focus-within/source-search:text-slate-500 dark:text-muted-foreground dark:group-focus-within/source-search:text-foreground/80" />
          <input
            type="search"
            value={sourceQuery}
            onChange={(event) => setSourceQuery(event.target.value)}
            aria-label="Search sources"
            placeholder="Search sources, topics, or descriptions..."
            className="h-10 w-full rounded-full border border-slate-200/80 bg-white pl-11 pr-12 text-sm text-slate-950 shadow-[0_1px_2px_rgba(15,23,42,0.03)] outline-none transition-all placeholder:text-slate-400 hover:border-slate-300 hover:bg-slate-50/40 focus:border-slate-300 focus:bg-white focus:ring-4 focus:ring-stone-950/2.5 sm:h-11 dark:border-border dark:bg-muted/30 dark:text-foreground dark:shadow-none dark:placeholder:text-muted-foreground dark:hover:border-foreground/18 dark:hover:bg-muted/45 dark:focus:border-ring/40 dark:focus:ring-ring/10"
          />
          {sourceQuery.length > 0 && (
            <button
              type="button"
              onClick={() => setSourceQuery('')}
              aria-label="Clear source search"
              className="absolute right-2 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 dark:text-muted-foreground dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35"
            >
              <XIcon className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <SourceFilterBar
        selected={sourceFilter}
        onSelect={setSourceFilter}
        types={filterTypes}
      />

      <div className="space-y-8">
        {isLoading ? (
          <SourceGroupSkeleton />
        ) : isError ? (
          <ArticleListState
            title="Could not load sources"
            description="Please refresh the page or try again in a moment."
            icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
          />
        ) : groups.length === 0 ? (
          normalizedSourceQuery ? (
            <ArticleListState
              title={
                sourceFilter === 'all'
                  ? `No sources found for "${sourceQuery.trim()}".`
                  : `No sources found in ${SOURCE_FILTER_LABELS[sourceFilter]} for "${sourceQuery.trim()}".`
              }
              description="Try searching for a source name, topic, category, or clear filters."
              icon={<SearchIcon className="h-5 w-5 stroke-[1.5]" />}
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSourceQuery('')}
                    className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                  >
                    Clear search
                  </button>
                  {sourceFilter !== 'all' && (
                    <button
                      type="button"
                      onClick={() => setSourceFilter('all')}
                      className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                    >
                      Show all sources
                    </button>
                  )}
                </div>
              }
            />
          ) : sourceFilter === 'following' ? (
            <ArticleListState
              title="You're not following any sources yet."
              description="Follow sources to personalize your AI Signal feed."
              icon={<BookmarkIcon className="h-5 w-5 stroke-[1.5]" />}
              action={
                <button
                  type="button"
                  onClick={() => setSourceFilter('all')}
                  className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Browse all sources
                </button>
              }
            />
          ) : (
            <ArticleListState
              title={
                sourceFilter === 'all'
                  ? 'No sources yet'
                  : `No sources found in ${SOURCE_FILTER_LABELS[sourceFilter]}.`
              }
              description={
                sourceFilter === 'all'
                  ? 'Sources will appear here as soon as they are available.'
                  : 'Try another category or clear filters.'
              }
              action={
                sourceFilter !== 'all' && (
                  <button
                    type="button"
                    onClick={() => setSourceFilter('all')}
                    className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                  >
                    Show all sources
                  </button>
                )
              }
            />
          )
        ) : (
          groups.map((group) => (
            <SourceSection
              key={group.type}
              type={group.type}
              items={group.items}
              sourceFilter={sourceFilter}
              preferredSources={preferredSources}
              updatingSource={updatingSource}
              isSaving={isSaving}
              followDisabled={followDisabled}
              userIsLoggedIn={userIsLoggedIn}
              onTogglePreferredSource={togglePreferredSource}
            />
          ))
        )}
      </div>
      <Outlet />
    </PageContainer>
  )
}
