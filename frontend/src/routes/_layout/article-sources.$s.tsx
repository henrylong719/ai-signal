import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { AlertCircleIcon, ArrowLeftIcon } from "lucide-react"
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
    <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
      <header className="pt-12 pb-5 border-b border-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
          <div className="max-w-2xl w-full">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <Skeleton className="h-10 w-56 rounded" />
              <Skeleton className="h-7 w-24 rounded-md" />
              <Skeleton className="h-7 w-28 rounded-md" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-5 w-full max-w-xl rounded" />
              <Skeleton className="h-5 w-3/4 max-w-lg rounded" />
            </div>
          </div>
        </div>
      </header>

      <div className="py-8">
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
      </div>
    </div>
  )
}

function ArticlesSources() {
  const { s } = Route.useParams()

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
      <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
        <ArticleListState
          title="Could not load source"
          description="Please refresh the page or try again in a moment."
          icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
          action={
            <Link
              to="/all-article-sources"
              className="inline-flex h-9 items-center rounded-md border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
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
      <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
        <ArticleListState
          title="Source not found"
          description="This source may have been removed or renamed."
          action={
            <Link
              to="/all-article-sources"
              className="inline-flex h-9 items-center rounded-md border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
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
    <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
      <header className="pt-10 pb-5 border-b border-slate-100">
        <div className="flex flex-col sm:flex-col sm:items-center justify-center items-center gap-6">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-serif text-3xl sm:text-4xl font-medium text-slate-900 tracking-tight">
              {capitalize(source.name)}
            </h1>
          </div>
          <p className="text-lg text-slate-500 leading-relaxed font-serif">
            {source.description}
          </p>
        </div>
      </header>

      <ArticleList
        {...feed}
        emptyTitle={`No articles from ${source.name} yet`}
        emptyDescription="New articles from this source will appear here when they are available."
        errorTitle={`Could not load articles from ${source.name}`}
      />
    </div>
  )
}
