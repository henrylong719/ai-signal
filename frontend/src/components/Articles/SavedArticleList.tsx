import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AlertCircleIcon, BookmarkIcon, LogInIcon } from "lucide-react"
import { ArticlesService } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"
import { useSavedArticles } from "@/hooks/useSavedArticles"
import { ArticleCard } from "./ArticleCard"
import { ArticleCardSkeleton } from "./ArticleCardSkeleton"
import { ArticleListState } from "./ArticleList"

export function SavedArticleList() {
  const { savedArticleIds, toggleSave } = useSavedArticles()
  const loggedIn = isLoggedIn()

  const { data, isPending, isError } = useQuery({
    queryKey: ["savedArticles"],
    queryFn: () => ArticlesService.readSavedArticles({}),
    enabled: loggedIn,
  })

  if (!loggedIn) {
    return (
      <ArticleListState
        title="Sign in to build your library"
        description="Saved articles are tied to your account so you can return to them later."
        icon={<LogInIcon className="h-5 w-5 stroke-[1.5]" />}
        action={
          <Link
            to="/login"
            className="inline-flex h-9 items-center rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2"
          >
            Sign in
          </Link>
        }
      />
    )
  }

  if (isPending) {
    return (
      <div className="py-8">
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
      </div>
    )
  }

  const articles = data?.data ?? []

  if (isError) {
    return (
      <ArticleListState
        title="Could not load your library"
        description="Please refresh the page or try again in a moment."
        icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
      />
    )
  }

  if (articles.length === 0) {
    return (
      <ArticleListState
        title="No saved articles yet"
        description="Click the bookmark icon on any article to save it here."
        icon={<BookmarkIcon className="h-5 w-5 stroke-[1.5]" />}
      />
    )
  }

  return (
    <div className="border-y border-slate-200/80 bg-white">
      {articles.map((article) => (
        <ArticleCard
          article={article}
          key={article.id}
          onBookmark={(e) => {
            e.preventDefault()
            toggleSave(article.id)
          }}
          isBookmarked={savedArticleIds.has(article.id)}
        />
      ))}
    </div>
  )
}
