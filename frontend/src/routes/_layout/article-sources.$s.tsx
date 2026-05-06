import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useLocation } from "@tanstack/react-router"
import { AlertCircleIcon, ArrowLeftIcon, RadioTowerIcon } from "lucide-react"
import { ArticlesService } from "@/client"
import { ArticleCardSkeleton } from "@/components/Articles/ArticleCardSkeleton"
import {
  ArticleList,
  ArticleListState,
} from "@/components/Articles/ArticleList"
import { Skeleton } from "@/components/ui/skeleton"
import { useArticleFeed } from "@/hooks/useArticleFeed"
import { capitalize } from "@/lib/utils"

export const Route = createFileRoute("/_layout/article-sources/$s")({
  component: ArticlesSources,
})

function ArticleSourceSkeleton() {
  return (
    <div className="mx-auto w-full max-w-5xl pb-16 pt-10 sm:pb-20 sm:pt-12">
      <header className="mb-7 border-b border-slate-200/80 pb-7">
        <Skeleton className="h-9 w-32 rounded-md" />
        <div className="mt-8 max-w-2xl">
          <Skeleton className="h-4 w-24 rounded" />
          <Skeleton className="mt-4 h-10 w-72 max-w-full rounded" />
          <Skeleton className="mt-3 h-5 w-full max-w-xl rounded" />
        </div>
      </header>

      <div className="max-w-4xl rounded-lg border border-slate-200/80 bg-white px-5 sm:px-6">
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
      </div>
    </div>
  )
}

function ArticlesSources() {
  const { s } = Route.useParams()
  const location = useLocation()
  const articleSourcesState = location.state as {
    allArticleSourcesFilter?: unknown
    allArticleSourcesScrollY?: unknown
  }
  const allArticleSourcesScrollY = articleSourcesState.allArticleSourcesScrollY
  const backToAllSourcesState =
    typeof allArticleSourcesScrollY === "number"
      ? (previousState: object) =>
          ({
            ...previousState,
            allArticleSourcesFilter:
              articleSourcesState.allArticleSourcesFilter,
            allArticleSourcesScrollY,
          }) as never
      : undefined

  const feed = useArticleFeed({ source: s })

  const sourcesQuery = useQuery({
    queryKey: ["articleSources"],
    queryFn: () => ArticlesService.readSources(),
  })

  const source = sourcesQuery.data?.data.find((source) => source.name === s)

  if (sourcesQuery.isLoading) {
    return <ArticleSourceSkeleton />
  }

  if (sourcesQuery.isError) {
    return (
      <div className="mx-auto w-full max-w-3xl pt-10">
        <ArticleListState
          title="Could not load source"
          description="Please refresh the page or try again in a moment."
          icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
          action={
            <Link
              to="/all-article-sources"
              state={backToAllSourcesState}
              className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2"
            >
              <ArrowLeftIcon className="mr-2 h-4 w-4" />
              Back to sources
            </Link>
          }
        />
      </div>
    )
  }

  if (!source) {
    return (
      <div className="mx-auto w-full max-w-3xl pt-10">
        <ArticleListState
          title="Source not found"
          description="This source may have been removed or renamed."
          action={
            <Link
              to="/all-article-sources"
              state={backToAllSourcesState}
              className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2"
            >
              <ArrowLeftIcon className="mr-2 h-4 w-4" />
              Back to sources
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-5xl pb-16 pt-10 sm:pb-20 sm:pt-12">
      <Link
        to="/all-article-sources"
        state={backToAllSourcesState}
        className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2"
      >
        <ArrowLeftIcon className="mr-2 h-4 w-4" />
        Back to sources
      </Link>

      <header className="mb-7 mt-8 flex flex-col gap-5 border-b border-slate-200/80 pb-7 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="mb-3 text-xs font-semibold uppercase text-slate-500">
            Source
          </p>
          <h1 className="font-display text-3xl font-semibold text-slate-950 sm:text-4xl">
            {capitalize(source.name)}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-slate-500">
            {source.description}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 self-start md:self-auto">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm">
            <RadioTowerIcon className="h-4 w-4 stroke-[1.8] text-slate-400" />
            {source.source_type}
          </div>
          <div className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm">
            {source.topic}
          </div>
        </div>
      </header>

      <div className="max-w-4xl">
        <ArticleList
          {...feed}
          emptyTitle={`No articles from ${source.name} yet`}
          emptyDescription="New articles from this source will appear here when they are available."
          errorTitle={`Could not load articles from ${source.name}`}
        />
      </div>
    </div>
  )
}
