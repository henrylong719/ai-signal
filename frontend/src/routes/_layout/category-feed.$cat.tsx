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
    <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
      <div className="sticky top-20 z-40 -mx-4 overflow-x-auto border-b border-slate-200 bg-white px-4 pt-6 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="flex w-max min-w-full gap-8">
          {CATEGORIES.map((tab) => (
            <Link
              key={tab}
              to="/category-feed/$cat"
              params={{ cat: tab }}
              aria-current={cat === tab ? "page" : undefined}
              className={`relative shrink-0 rounded-sm pb-5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 ${
                cat === tab
                  ? "text-slate-900"
                  : "text-slate-400 hover:text-slate-600"
              }`}
            >
              {capitalize(tab)}
              {cat === tab && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-900 rounded-full" />
              )}
            </Link>
          ))}
        </div>
      </div>

      <ArticleList
        {...feed}
        emptyTitle={`No ${capitalize(cat)} articles yet`}
        emptyDescription="New articles for this topic will appear here when they are available."
        errorTitle={`Could not load ${capitalize(cat)} articles`}
      />
    </div>
  )
}
