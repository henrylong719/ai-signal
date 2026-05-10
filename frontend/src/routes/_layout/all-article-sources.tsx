import { createFileRoute, Outlet, useLocation } from '@tanstack/react-router'
import { AlertCircleIcon, BookmarkIcon } from 'lucide-react'
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { source_type } from '@/client'
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

  const filteredSources =
    sourceFilter === 'all'
      ? sources
      : sourceFilter === 'following'
        ? followedSources
        : sources.filter((source) => source.source_type === sourceFilter)

  const groups: Array<{
    type: Exclude<source_types, 'all'>
    items: typeof sources
  }> =
    sourceFilter === 'following'
      ? followedSources.length > 0
        ? [{ type: 'following', items: followedSources }]
        : []
      : SOURCE_TYPES.filter(
          (type): type is source_type => type !== 'all' && type !== 'following',
        )
          .map((type) => ({
            type,
            items: filteredSources.filter(
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

      <SourceFilterBar
        selected={sourceFilter}
        onSelect={setSourceFilter}
        types={filterTypes}
      />

      <div className="space-y-10">
        {isLoading ? (
          <SourceGroupSkeleton />
        ) : isError ? (
          <ArticleListState
            title="Could not load sources"
            description="Please refresh the page or try again in a moment."
            icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
          />
        ) : groups.length === 0 ? (
          sourceFilter === 'following' ? (
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
                  : `No ${SOURCE_FILTER_LABELS[sourceFilter]} sources yet`
              }
              description="Sources will appear here as soon as they are available."
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
