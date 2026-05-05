import { createFileRoute } from "@tanstack/react-router"
import { ArticleList } from "@/components/Articles/ArticleList"
import { useArticleFeed } from "@/hooks/useArticleFeed"

export const Route = createFileRoute("/_layout/search-feed/$q")({
  component: SearchFeed,
})

function SearchFeed() {
  const { q } = Route.useParams()

  const feed = useArticleFeed({ search: q })

  return (
    <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
      <header className="pt-10 pb-8">
        <div className="text-center pb-5">
          <h1 className="font-serif text-3xl sm:text-4xl font-medium text-slate-900 mb-3 tracking-tight">
            Search results
          </h1>
          <p className="break-words text-lg text-slate-500 leading-relaxed font-serif">
            Results for "{q}"
          </p>
        </div>
      </header>
      <ArticleList
        {...feed}
        emptyTitle={`No results for "${q}"`}
        emptyDescription="Try a different phrase or browse the latest AI signals."
        errorTitle="Could not load search results"
      />
    </div>
  )
}
