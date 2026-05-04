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
      <div className="border-b border-slate-200 pt-6 sticky top-20 bg-white z-40">
        <div className="flex gap-10">
          {CATEGORIES.map((tab) => (
            <Link
              key={tab}
              to="/category-feed/$cat"
              params={{ cat: tab }}
              className={`pb-5 text-sm font-medium transition-colors relative ${
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

      <ArticleList {...feed} />
    </div>
  )
}
