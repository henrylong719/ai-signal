import { createFileRoute, Link } from '@tanstack/react-router'
import type { category } from '@/client'
import { ArticleList } from '@/components/Articles/ArticleList'
import { useArticleFeed } from '@/hooks/useArticleFeed'
import { CATEGORIES } from '@/lib/constants'
import { capitalize } from '@/lib/utils'

export const Route = createFileRoute('/_layout/category-feed/$cat')({
  component: CategoryFeed,
})

function CategoryFeed() {
  const { cat } = Route.useParams()
  const feed = useArticleFeed({ category: cat as category })

  return (
    <div className="mx-auto w-full max-w-4xl pb-16 pt-10 sm:pb-20 sm:pt-12">
      <header className="mb-7 border-b border-slate-200/80 pb-7 dark:border-border">
        <p className="mb-3 text-xs font-semibold uppercase text-slate-500 dark:text-muted-foreground">
          Topic
        </p>
        <h1 className="font-display text-3xl font-semibold text-slate-950 sm:text-4xl dark:text-foreground">
          {capitalize(cat)}
        </h1>
        <p className="mt-3 max-w-xl text-base leading-7 text-slate-500 dark:text-muted-foreground">
          Latest signals filtered to this topic.
        </p>
      </header>

      <div className="sticky top-16 z-40 -mx-4 mb-6 overflow-x-auto border-y border-slate-200/80 bg-white/95 px-4 py-2.5 backdrop-blur sm:top-[72px] sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8 dark:border-border dark:bg-background/92 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="flex w-max min-w-full gap-2">
          {CATEGORIES.map((tab) => (
            <Link
              key={tab}
              to="/category-feed/$cat"
              params={{ cat: tab }}
              aria-current={cat === tab ? 'page' : undefined}
              className={`shrink-0 rounded-full border px-3.5 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background ${
                cat === tab
                  ? 'border-slate-950 bg-slate-950 text-white shadow-sm dark:border-primary dark:bg-primary dark:text-primary-foreground'
                  : 'border-slate-200/70 bg-white text-slate-600 shadow-sm hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent/70 dark:hover:text-foreground'
              }`}
            >
              {capitalize(tab)}
            </Link>
          ))}
        </div>
      </div>
      <div>
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
