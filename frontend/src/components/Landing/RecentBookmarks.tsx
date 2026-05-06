import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { BookmarkIcon, ChevronRightIcon } from "lucide-react"
import { ArticlesService } from "@/client"
import { Skeleton } from "@/components/ui/skeleton"
import { isLoggedIn } from "@/hooks/useAuth"
import { redirectHref } from "@/lib/article-urls"

const RecentBookmarks = () => {
  const loggedIn = isLoggedIn()

  const { data, isLoading, isError } = useQuery({
    queryKey: ["savedArticles"],
    queryFn: () => ArticlesService.readSavedArticles({}),
    enabled: loggedIn,
  })

  const articles = data?.data.slice(0, 3) ?? []

  return (
    <div>
      <div className="mb-4 flex items-center gap-2.5">
        <div className="text-slate-400 dark:text-muted-foreground">
          <BookmarkIcon className="h-4 w-4 stroke-[1.6]" />
        </div>
        <span className="text-sm font-semibold text-slate-500 dark:text-muted-foreground">
          Your saved articles
        </span>
      </div>
      <div className="mt-2 space-y-5">
        {isLoading ? (
          ["a", "b", "c"].map((key) => (
            <div key={key} className="flex items-start gap-4">
              <Skeleton className="h-8 w-6 rounded bg-slate-100 dark:bg-muted" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-full rounded bg-slate-100 dark:bg-muted" />
                <Skeleton className="h-3 w-24 rounded bg-slate-100 dark:bg-muted" />
              </div>
            </div>
          ))
        ) : isError ? (
          <p className="rounded-lg border border-slate-100 bg-white p-3 text-sm text-slate-500 dark:border-border dark:bg-card/45 dark:text-muted-foreground">
            Could not load saved articles.
          </p>
        ) : articles.length === 0 ? (
          <p className="rounded-lg border border-slate-100 bg-white p-3 text-sm text-slate-500 dark:border-border dark:bg-card/45 dark:text-muted-foreground">
            Saved articles will appear here.
          </p>
        ) : (
          articles.map((article, index) => (
            <div key={article.id} className="group flex items-start gap-4">
              <span className="mt-1 font-serif text-2xl font-medium leading-none text-slate-200 transition-colors group-hover:text-slate-300 dark:text-muted dark:group-hover:text-muted-foreground/45">
                0{index + 1}
              </span>
              <div>
                <a
                  href={redirectHref(article.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  <h4 className="mb-1.5 font-serif font-medium leading-snug text-slate-950 transition-colors group-hover:text-slate-700 dark:text-foreground dark:group-hover:text-foreground/78">
                    {article.title}
                  </h4>
                </a>
                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  <span className="text-slate-600 dark:text-muted-foreground">
                    {article.source}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <Link
        to="/saved-articles"
        className="mt-4 inline-flex items-center rounded-sm text-xs font-semibold text-slate-500 transition-colors hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-muted-foreground dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
      >
        See all saved articles{" "}
        <ChevronRightIcon className="w-3 h-3 ml-0.5 stroke-2" />
      </Link>
    </div>
  )
}

export default RecentBookmarks
