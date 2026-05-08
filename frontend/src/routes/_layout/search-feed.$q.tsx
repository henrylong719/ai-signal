import { createFileRoute } from '@tanstack/react-router'
import { SearchIcon } from 'lucide-react'
import { ArticleList } from '@/components/Articles/ArticleList'
import { useArticleFeed } from '@/hooks/useArticleFeed'

export const Route = createFileRoute('/_layout/search-feed/$q')({
  component: SearchFeed,
})

function SearchFeed() {
  const { q } = Route.useParams()

  const feed = useArticleFeed({ search: q })

  return (
    <div className="mx-auto w-full max-w-4xl pb-16 pt-10 sm:pb-20 sm:pt-12">
      <header className="mb-7 flex flex-col gap-5 border-b border-slate-200/80 pb-7 md:flex-row md:items-end md:justify-between dark:border-border">
        <div className="max-w-2xl">
          <p className="mb-3 text-xs font-semibold uppercase text-slate-500 dark:text-muted-foreground">
            Search
          </p>
          <h1 className="font-display text-3xl font-semibold text-slate-950 sm:text-4xl dark:text-foreground">
            Search results
          </h1>
          <p className="mt-3 max-w-xl break-words text-base leading-7 text-slate-500 dark:text-muted-foreground">
            Articles matching your query.
          </p>
        </div>
        <div className="inline-flex max-w-full items-center gap-2 self-start rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm md:self-auto dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none">
          <SearchIcon className="h-4 w-4 stroke-[1.8] text-slate-400 dark:text-muted-foreground" />
          <span className="truncate">{q}</span>
        </div>
      </header>
      <div>
        <ArticleList
          {...feed}
          emptyTitle={`No results for "${q}"`}
          emptyDescription="Try a different phrase or browse the latest AI signals."
          errorTitle="Could not load search results"
        />
      </div>
    </div>
  )
}
