import { createFileRoute, Link } from "@tanstack/react-router"
import type { category } from "@/client"
import { ArticleList } from "@/components/Articles/ArticleList"
import { useArticleFeed } from "@/hooks/useArticleFeed"
import { CATEGORIES } from "@/lib/constants"
import { capitalize } from "@/lib/utils"

export const Route = createFileRoute("/_layout/category-feed/$cat")({
  component: CategoryFeed,
})

function CategoryFeed() {
  const { cat } = Route.useParams()
  const feed = useArticleFeed({ category: cat as category })

  return (
    <div className="mx-auto w-full max-w-5xl pb-16 pt-8 sm:pb-20 sm:pt-10">
      <header className="mb-6 border-b border-slate-200/70 pb-6">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
          Topic
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          {capitalize(cat)}
        </h1>
        <p className="mt-3 max-w-xl text-base leading-7 text-slate-500">
          Latest signals filtered to this topic.
        </p>
      </header>

      <div className="sticky top-20 z-40 -mx-6 mb-6 overflow-x-auto border-y border-slate-200 bg-white/90 px-6 py-2 backdrop-blur md:-mx-8 md:px-8 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="flex w-max min-w-full gap-2">
          {CATEGORIES.map((tab) => (
            <Link
              key={tab}
              to="/category-feed/$cat"
              params={{ cat: tab }}
              aria-current={cat === tab ? "page" : undefined}
              className={`shrink-0 rounded-full border px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 ${
                cat === tab
                  ? "border-slate-950 bg-slate-950 text-white shadow-sm"
                  : "border-transparent text-slate-600 hover:border-slate-200 hover:bg-slate-50 hover:text-slate-950"
              }`}
            >
              {capitalize(tab)}
            </Link>
          ))}
        </div>
      </div>
      <div className="max-w-4xl">
        <ArticleList
          {...feed}
          emptyTitle={`No ${capitalize(cat)} articles yet`}
          emptyDescription="New articles for this topic will appear here when they are available."
          errorTitle={`Could not load ${capitalize(cat)} articles`}
        />
      </div>
    </div>
  )
}
