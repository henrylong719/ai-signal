import { useQuery } from '@tanstack/react-query'
import {
  createFileRoute,
  Link,
  Outlet,
  useLocation,
} from '@tanstack/react-router'
import { AlertCircleIcon, ArrowRightIcon, RadioTowerIcon } from 'lucide-react'
import { useLayoutEffect, useRef, useState } from 'react'
import { ArticlesService, type source_type } from '@/client'
import { ArticleListState } from '@/components/Articles/ArticleList'
import { Skeleton } from '@/components/ui/skeleton'
import { capitalize, cn } from '@/lib/utils'

export const Route = createFileRoute('/_layout/all-article-sources')({
  component: AllArticleSources,
})

export type source_types = 'all' | source_type

const SOURCE_TYPES: source_types[] = [
  'all',
  'official',
  'independent',
  'research',
  'media',
  'newsletter',
  'community',
]

const isSourceType = (value: unknown): value is source_types =>
  typeof value === 'string' && SOURCE_TYPES.includes(value as source_types)

const SOURCE_SKELETON_GROUPS = ['official', 'research', 'media']
const SOURCE_SKELETON_ITEMS = ['first', 'second', 'third', 'fourth']

function SourceGroupSkeleton() {
  return (
    <div className="space-y-5">
      {SOURCE_SKELETON_GROUPS.map((group) => (
        <section key={group}>
          <div className="mb-3 flex items-center justify-between gap-4 px-1">
            <Skeleton className="h-5 w-28 rounded" />
            <Skeleton className="h-7 w-10 rounded-full" />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {SOURCE_SKELETON_ITEMS.map((item) => (
              <div
                key={`${group}-${item}`}
                className="flex min-h-36 flex-col justify-between gap-4 rounded-lg border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] sm:flex-row sm:items-start dark:border-border dark:bg-card/35 dark:shadow-none"
              >
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <Skeleton className="h-5 w-36 rounded" />
                    <Skeleton className="h-5 w-20 rounded" />
                    <Skeleton className="h-5 w-24 rounded" />
                  </div>
                  <Skeleton className="h-4 w-full max-w-md rounded" />
                </div>
                <Skeleton className="hidden h-8 w-8 shrink-0 rounded-md sm:block" />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

function AllArticleSources() {
  const location = useLocation()
  const savedRouteState = location.state as {
    allArticleSourcesFilter?: unknown
    allArticleSourcesScrollY?: unknown
  }
  const [sourceFilter, setSourceFilter] = useState<source_types>(() =>
    isSourceType(savedRouteState.allArticleSourcesFilter)
      ? savedRouteState.allArticleSourcesFilter
      : 'all',
  )
  const hasRestoredScroll = useRef(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['articleSources'],
    queryFn: () => ArticlesService.readSources(),
  })

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

  const filteredSources =
    sourceFilter === 'all'
      ? data?.data
      : data?.data.filter((s) => s.source_type === sourceFilter)

  const groups = SOURCE_TYPES.filter((type) => type !== 'all')
    .map((type) => ({
      type,
      items: filteredSources?.filter((s) => s.source_type === type),
    }))
    .filter((group) => (group.items || []).length > 0)

  const sourceCount = data?.data.length ?? 0

  return (
    <div className="mx-auto w-full max-w-5xl pb-16 pt-10 sm:pb-20 sm:pt-12">
      <header className="mb-7 flex flex-col gap-5 border-b border-slate-200/80 pb-7 md:flex-row md:items-end md:justify-between dark:border-border">
        <div className="max-w-2xl">
          <p className="mb-3 text-xs font-semibold uppercase text-slate-500 dark:text-muted-foreground">
            Directory
          </p>
          <h1 className="font-display text-3xl font-semibold text-slate-950 sm:text-4xl dark:text-foreground">
            Sources
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-slate-500 dark:text-muted-foreground">
            Explore the official publications, research feeds, media outlets,
            newsletters, independent writers, and community sites behind AI
            Signal.
          </p>
        </div>
        <div className="inline-flex max-w-full items-center gap-2 self-start rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm md:self-auto dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none">
          <RadioTowerIcon className="h-4 w-4 stroke-[1.8] text-slate-400 dark:text-muted-foreground" />
          <span>
            {isLoading ? 'Loading sources' : `${sourceCount} sources`}
          </span>
        </div>
      </header>

      <div className="mb-6 rounded-lg border border-slate-200/80 bg-white p-2 shadow-[0_1px_2px_rgba(15,23,42,0.03)] dark:border-border dark:bg-transparent dark:shadow-none">
        <div className="flex flex-wrap gap-2">
          {SOURCE_TYPES.map((type) => (
            <button
              type="button"
              key={type}
              onClick={() => setSourceFilter(type)}
              className={cn(
                'min-h-9 rounded-full border px-3.5 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
                sourceFilter === type
                  ? 'border-slate-950 bg-slate-950 text-white shadow-sm dark:border-primary dark:bg-primary dark:text-primary-foreground'
                  : 'border-slate-200/70 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:hover:border-foreground/18 dark:hover:bg-accent/70 dark:hover:text-foreground',
              )}
            >
              {capitalize(type)}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-5">
        {isLoading ? (
          <SourceGroupSkeleton />
        ) : isError ? (
          <ArticleListState
            title="Could not load sources"
            description="Please refresh the page or try again in a moment."
            icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
          />
        ) : groups.length === 0 ? (
          <ArticleListState
            title={
              sourceFilter === 'all'
                ? 'No sources yet'
                : `No ${capitalize(sourceFilter)} sources yet`
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
        ) : (
          groups.map(
            (group) =>
              group.items && (
                <section key={group.type}>
                  <div className="mb-3 flex items-center justify-between gap-4 px-1">
                    <h2 className="text-sm font-semibold text-slate-950 dark:text-foreground">
                      {capitalize(group.type)}
                    </h2>
                    <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-500 dark:border-border dark:bg-transparent dark:text-muted-foreground">
                      {group.items.length}
                    </span>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    {group.items.map((source) => (
                      <Link
                        key={source.name}
                        to="/article-sources/$s"
                        params={{ s: source.name }}
                        state={(previousState) => ({
                          ...previousState,
                          allArticleSourcesFilter: sourceFilter,
                          allArticleSourcesScrollY: window.scrollY,
                        })}
                        className="group block min-h-36 rounded-lg border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.03)] transition-all hover:border-slate-300 hover:bg-slate-50/70 hover:shadow-[0_1px_2px_rgba(15,23,42,0.04),0_10px_24px_rgba(15,23,42,0.05)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-card/35 dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-card/65 dark:hover:shadow-none dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <div className="mb-2 flex flex-wrap items-center gap-2">
                              <h3 className="text-base font-semibold text-slate-950 dark:text-foreground">
                                {source.name}
                              </h3>
                              <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-500 dark:border-border dark:bg-transparent dark:text-muted-foreground">
                                {source.source_type}
                              </span>
                              <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-500 dark:border-border dark:bg-transparent dark:text-muted-foreground">
                                {source.topic}
                              </span>
                            </div>
                            <p className="line-clamp-2 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
                              {source.description}
                            </p>
                          </div>
                          <div className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-400 shadow-sm transition-colors group-hover:text-slate-950 sm:flex dark:border-border dark:bg-muted/35 dark:text-muted-foreground dark:shadow-none dark:group-hover:text-foreground">
                            <ArrowRightIcon className="h-4 w-4 stroke-[1.7]" />
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </section>
              ),
          )
        )}
      </div>
      <Outlet />
    </div>
  )
}
