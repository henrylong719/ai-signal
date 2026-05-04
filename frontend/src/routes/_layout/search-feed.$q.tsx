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
      <header className="pt-12 pb-5 border-b border-slate-100">
        <h1 className="font-serif text-3xl sm:text-4xl font-medium text-slate-900 tracking-tight">
          Search results
        </h1>
        <p className="mt-3 break-words text-lg text-slate-500 leading-relaxed font-serif">
          Results for "{q}"
        </p>
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
