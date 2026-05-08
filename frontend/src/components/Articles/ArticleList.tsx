import { AlertCircleIcon, NewspaperIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import type { ArticlePublic } from '@/client'
import { useDismissArticle } from '@/hooks/useArticleEvents'
import useAuth, { isLoggedIn } from '@/hooks/useAuth'
import useCustomToast from '@/hooks/useCustomToast'
import { useSavedArticles } from '@/hooks/useSavedArticles'
import { ArticleCard } from './ArticleCard'
import { ArticleCardSkeleton } from './ArticleCardSkeleton'

interface ArticleListProps {
  articles: ArticlePublic[]
  feedStatus: string | null
  loadMoreRef: (node: HTMLDivElement | null) => void
  isPending: boolean
  isError: boolean
  emptyTitle?: string
  emptyDescription?: string
  errorTitle?: string
  errorDescription?: string
  /**
   * Show a dismiss button on each card. Currently set only by the
   * For-You feed; other feeds leave it false because dismissals only
   * affect what the recommender shows you, not the chronological lists.
   */
  showDismiss?: boolean
  /**
   * Map of article id → recommendation reason badge. Set by the For-You
   * feed; chronological feeds leave it undefined and no badges render.
   */
  reasons?: Map<string, string | null>
}

interface ArticleListStateProps {
  title: string
  description: string
  icon?: ReactNode
  action?: ReactNode
}

export function ArticleListState({
  title,
  description,
  icon,
  action,
}: ArticleListStateProps) {
  return (
    <div className="mx-auto my-10 max-w-2xl rounded-lg border border-slate-200/80 bg-white px-6 py-12 text-center shadow-[0_1px_2px_rgba(15,23,42,0.03),0_18px_45px_rgba(15,23,42,0.035)] dark:border-border dark:bg-card/55 dark:shadow-none">
      <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 text-slate-400 ring-1 ring-slate-200/80 dark:bg-muted dark:text-muted-foreground dark:ring-border">
        {icon ?? <NewspaperIcon className="h-5 w-5 stroke-[1.5]" />}
      </div>
      <h2 className="font-serif text-xl font-medium text-slate-950 dark:text-foreground">
        {title}
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-600 dark:text-muted-foreground">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ArticleList({
  articles,
  feedStatus,
  loadMoreRef,
  isPending,
  isError,
  emptyTitle = 'No articles yet',
  emptyDescription = 'New signals will appear here as soon as they are available.',
  errorTitle = 'Could not load articles',
  errorDescription = 'Please refresh the page or try again in a moment.',
  showDismiss = false,
  reasons,
}: ArticleListProps) {
  const { savedArticleIds, toggleSave } = useSavedArticles()
  const { dismissedIds, dismiss } = useDismissArticle()
  const { user } = useAuth()
  const { showErrorToast } = useCustomToast()
  const [pendingSaveArticleId, setPendingSaveArticleId] = useState<
    string | null
  >(null)

  useEffect(() => {
    if (!user || !pendingSaveArticleId) {
      return
    }

    if (!savedArticleIds.has(pendingSaveArticleId)) {
      toggleSave(pendingSaveArticleId)
    }
    setPendingSaveArticleId(null)
  }, [pendingSaveArticleId, savedArticleIds, toggleSave, user])

  const handleBookmark = (articleId: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    if (!isLoggedIn()) {
      setPendingSaveArticleId(articleId)
      return
    }
    toggleSave(articleId)
  }

  const handleBookmarkAuthRequired = (articleId: string) => () => {
    setPendingSaveArticleId(articleId)
  }

  // Dismiss handler is only wired when showDismiss is true. Optimistic
  // removal happens through the dismissedIds filter below; the mutation
  // hook handles rollback on error.
  const handleDismiss = (articleId: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    if (!isLoggedIn()) {
      showErrorToast('Please login to personalize your feed!')
      return
    }
    dismiss(articleId)
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
      <ArticleListState
        title={errorTitle}
        description={errorDescription}
        icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
      />
    )
  }

  // Filter out optimistically-dismissed articles. Only relevant when
  // dismiss is enabled; on other feeds dismissedIds will still be
  // populated if the user dismissed elsewhere in the same session, but
  // we deliberately don't filter — Latest/Saved feeds should show what
  // they say they show.
  const visibleArticles = showDismiss
    ? articles.filter((article) => !dismissedIds.has(article.id))
    : articles

  if (visibleArticles.length === 0) {
    return (
      <ArticleListState title={emptyTitle} description={emptyDescription} />
    )
  }

  return (
    <div className="pb-2">
      {visibleArticles.map((article) => (
        <ArticleCard
          article={article}
          key={article.id}
          onBookmark={handleBookmark(article.id)}
          onBookmarkAuthRequired={handleBookmarkAuthRequired(article.id)}
          isBookmarked={savedArticleIds.has(article.id)}
          onDismiss={showDismiss ? handleDismiss(article.id) : undefined}
          reason={reasons?.get(article.id) ?? undefined}
        />
      ))}
      <div
        ref={loadMoreRef}
        className="py-8 text-center text-sm font-medium text-slate-500 dark:text-muted-foreground"
      >
        {feedStatus}
      </div>
    </div>
  )
}
