import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { AlertCircleIcon, BookmarkIcon, LogInIcon } from 'lucide-react'
import { useState } from 'react'
import { ArticlesService } from '@/client'
import AuthModal from '@/components/Auth/AuthModal'
import { isLoggedIn } from '@/hooks/useAuth'
import { useSavedArticles } from '@/hooks/useSavedArticles'
import { ArticleCard } from './ArticleCard'
import { ArticleCardSkeleton } from './ArticleCardSkeleton'
import { ArticleListState } from './ArticleList'

const SAVED_ARTICLES_STALE_TIME_MS = 1000 * 60

export function SavedArticleList() {
  const { savedArticleIds, toggleSave } = useSavedArticles()
  const loggedIn = isLoggedIn()
  const [actionStatus, setActionStatus] = useState('')

  const { data, isPending, isError } = useQuery({
    queryKey: ['savedArticles'],
    queryFn: () => ArticlesService.readSavedArticles({}),
    enabled: loggedIn,
    staleTime: SAVED_ARTICLES_STALE_TIME_MS,
  })

  if (!loggedIn) {
    return (
      <ArticleListState
        title="Sign in to build your library"
        description="Sign in to save articles, follow trusted sources, and tune your feed."
        icon={<LogInIcon className="h-5 w-5 stroke-[1.5]" />}
        action={
          <AuthModal
            title="Sign in to build your library"
            description="Sign in to save articles, follow trusted sources, and tune your feed."
            trigger={
              <button
                type="button"
                className="inline-flex h-9 items-center rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
              >
                Sign in
              </button>
            }
          />
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
        description="Bookmark articles from Latest or For You as you read — saved items stay in your library and help tune recommendations."
        icon={<BookmarkIcon className="h-5 w-5 stroke-[1.5]" />}
        action={
          <Link
            to="/personalization"
            className="inline-flex h-9 items-center rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            Tune your signal
          </Link>
        }
      />
    )
  }

  return (
    <div className="border-y border-slate-200/80 bg-white dark:border-border dark:bg-transparent">
      <span className="sr-only" role="status" aria-live="polite">
        {actionStatus}
      </span>
      {articles.map((article) => (
        <ArticleCard
          article={article}
          key={article.id}
          onBookmark={(e) => {
            e.preventDefault()
            setActionStatus(`Removed ${article.title} from saved articles.`)
            toggleSave(article.id)
          }}
          isBookmarked={savedArticleIds.has(article.id)}
        />
      ))}
    </div>
  )
}
