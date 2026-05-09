import { createFileRoute, Link, useLocation } from '@tanstack/react-router'
import { AlertCircleIcon, ArrowLeftIcon } from 'lucide-react'
import {
  ArticleList,
  ArticleListState,
} from '@/components/Articles/ArticleList'
import { PageContainer, PageHeader } from '@/components/Layout/Page'
import ArticleSourceSkeleton from '@/components/Source/ArticleSourceSkeleton'
import { useArticleFeed } from '@/hooks/useArticleFeed'
import { useSources } from '@/hooks/useSources'
import { capitalize } from '@/lib/utils'

export const Route = createFileRoute('/_layout/article-sources/$s')({
  component: ArticlesSources,
})

function ArticlesSources() {
  const { s } = Route.useParams()
  const location = useLocation()
  const articleSourcesState = location.state as {
    allArticleSourcesFilter?: unknown
    allArticleSourcesScrollY?: unknown
  }
  const allArticleSourcesScrollY = articleSourcesState.allArticleSourcesScrollY
  const backToAllSourcesState =
    typeof allArticleSourcesScrollY === 'number'
      ? (previousState: object) =>
          ({
            ...previousState,
            allArticleSourcesFilter:
              articleSourcesState.allArticleSourcesFilter,
            allArticleSourcesScrollY,
          }) as never
      : undefined

  const { dataUpdatedAt: _latestUpdatedAt, ...feed } = useArticleFeed({
    source: s,
  })

  const {
    sources,
    isLoading: sourcesLoading,
    isError: sourcesError,
  } = useSources()

  const source = sources.find((source) => source.name === s)

  if (sourcesLoading) {
    return <ArticleSourceSkeleton />
  }

  if (sourcesError) {
    return (
      <PageContainer variant="narrow" spacing="compact" className="max-w-3xl">
        <ArticleListState
          title="Could not load source"
          description="Please refresh the page or try again in a moment."
          icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
          action={
            <Link
              to="/all-article-sources"
              state={backToAllSourcesState}
              className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
            >
              <ArrowLeftIcon className="mr-2 h-4 w-4" />
              Back to sources
            </Link>
          }
        />
      </PageContainer>
    )
  }

  if (!source) {
    return (
      <PageContainer variant="narrow" spacing="compact" className="max-w-3xl">
        <ArticleListState
          title="Source not found"
          description="This source may have been removed or renamed."
          action={
            <Link
              to="/all-article-sources"
              state={backToAllSourcesState}
              className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
            >
              <ArrowLeftIcon className="mr-2 h-4 w-4" />
              Back to sources
            </Link>
          }
        />
      </PageContainer>
    )
  }

  return (
    <PageContainer variant="default">
      <Link
        to="/all-article-sources"
        state={backToAllSourcesState}
        className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-foreground/86 dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
      >
        <ArrowLeftIcon className="mr-2 h-4 w-4" />
        Back to sources
      </Link>

      <PageHeader
        className="mt-8"
        eyebrow="Source"
        title={capitalize(source.name)}
        description={source.description}
      >
        <p className="mt-4 flex flex-wrap items-center gap-2 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
          <span>{capitalize(source.source_type)}</span>
          <span
            aria-hidden="true"
            className="text-slate-300 dark:text-muted-foreground/45"
          >
            &bull;
          </span>
          <span>{capitalize(source.topic)}</span>
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
          Want this source to shape your For You feed?{' '}
          <Link
            to="/personalization"
            className="font-medium text-slate-800 underline decoration-slate-300 underline-offset-4 transition-colors hover:text-slate-950 hover:decoration-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-foreground/86 dark:decoration-border dark:hover:text-foreground dark:hover:decoration-foreground/45 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            Tune source preferences
          </Link>
          .
        </p>
      </PageHeader>

      <ArticleList
        {...feed}
        emptyTitle={`No articles from ${source.name} yet`}
        emptyDescription="New articles from this source will appear here when they are available."
        errorTitle={`Could not load articles from ${source.name}`}
      />
    </PageContainer>
  )
}
