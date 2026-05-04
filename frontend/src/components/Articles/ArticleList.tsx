import type { ArticlePublic } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { useSavedArticles } from "@/hooks/useSavedArticles"
import { ArticleCard } from "./ArticleCard"
import { ArticleCardSkeleton } from "./ArticleCardSkeleton"

interface ArticleListProps {
  articles: ArticlePublic[]
  feedStatus: string | null
  loadMoreRef: (node: HTMLDivElement | null) => void
  isPending: boolean
  isError: boolean
}

export function ArticleList({
  articles,
  feedStatus,
  loadMoreRef,
  isPending,
  isError,
}: ArticleListProps) {
  const { savedArticleIds, toggleSave } = useSavedArticles()
  const { showErrorToast } = useCustomToast()

  const handleBookmark = (articleId: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    if (!isLoggedIn()) {
      showErrorToast("Please login to save articles!")
      return
    }
    toggleSave(articleId)
  }

  if (isPending) {
    return (
      <div className="py-8">
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="py-8 text-sm text-slate-500">
        Could not load articles.
      </div>
    )
  }

  return (
    <div>
      {articles.map((article) => (
        <ArticleCard
          article={article}
          key={article.id}
          onBookmark={handleBookmark(article.id)}
          isBookmarked={savedArticleIds.has(article.id)}
        />
      ))}
      <div
        ref={loadMoreRef}
        className="py-8 text-center text-sm text-slate-500"
      >
        {feedStatus}
      </div>
    </div>
  )
}
