import { Link } from '@tanstack/react-router'
import { BookmarkIcon, ThumbsDown } from 'lucide-react'
import { DateTime } from 'luxon'
import type { ArticlePublic } from '@/client'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { isLoggedIn } from '@/hooks/useAuth'
import { redirectHref } from '@/lib/article-urls'
import { capitalize, cn } from '@/lib/utils'
import { Badge } from '../ui/badge'

interface ArticleCardProps {
  article: ArticlePublic
  featured?: boolean
  className?: string
  onBookmark?: (e: React.MouseEvent) => void
  isBookmarked?: boolean
  /**
   * If provided, renders a dismiss button next to the bookmark.
   * The For-You feed wires this; other feeds (Latest, Saved, etc.) leave
   * it unset, so the button is hidden.
   */
  onDismiss?: (e: React.MouseEvent) => void
  /**
   * Optional explainability badge ("Because you follow RAG", etc.).
   * Set by the For-You feed where articles are ranked by the recommender;
   * unset on chronological feeds where there's no ranking signal to explain.
   */
  reason?: string | null
}

export function ArticleCard({
  article,
  featured = false,
  className,
  onBookmark,
  isBookmarked = false,
  onDismiss,
  reason,
}: ArticleCardProps) {
  // Outbound links go through our redirect endpoint so we can record
  // the click as a behavioral signal for the recommender. Cookie auth
  // makes this work — the browser sends the access cookie on the
  // navigation. See lib/article-urls.ts for details.
  const href = redirectHref(article.id)
  const showActions = isLoggedIn()

  return (
    <article
      className={cn(
        'group -mx-3 border-b border-slate-200/70 px-3 py-7 transition-colors last:border-0 hover:bg-slate-50/60 sm:-mx-4 sm:px-4 sm:py-8 dark:border-border/80 dark:hover:bg-muted/30',
        className,
      )}
    >
      <div className="flex flex-col gap-4">
        {reason && (
          <div className="inline-flex w-fit rounded-full border border-stone-200 bg-stone-50 px-2.5 py-1 text-[11px] font-medium uppercase text-stone-700 dark:border-border/85 dark:bg-muted/55 dark:text-muted-foreground">
            {reason}
          </div>
        )}
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2 text-xs font-medium text-slate-500 dark:text-muted-foreground">
            <Link
              key={article.source}
              to="/article-sources/$s"
              params={{ s: article.source }}
            >
              <span className="truncate text-slate-900 hover:text-slate-950 dark:text-foreground/88 dark:hover:text-foreground">
                {article.source}
              </span>
            </Link>
            <span className="text-slate-300 dark:text-muted-foreground/45">
              &bull;
            </span>
            <span className="shrink-0">
              {article.published_at
                ? DateTime.fromISO(article.published_at).toLocaleString(
                    DateTime.DATE_MED,
                  )
                : ''}
            </span>
          </div>
          {showActions && (
            <div className="-mt-1 -mr-1 flex shrink-0 items-center gap-1 text-slate-400 dark:text-muted-foreground">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={onBookmark}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-white hover:text-slate-950 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:hover:bg-accent/80 dark:hover:text-foreground dark:hover:shadow-none dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                    aria-label={
                      isBookmarked ? 'Remove saved article' : 'Save article'
                    }
                    aria-pressed={isBookmarked}
                  >
                    <BookmarkIcon
                      className={cn(
                        'h-4.5 w-4.5 stroke-[1.6]',
                        isBookmarked &&
                          'fill-slate-900 text-slate-900 dark:fill-foreground dark:text-foreground',
                      )}
                    />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top">
                  {isBookmarked ? 'Remove saved article' : 'Save article'}
                </TooltipContent>
              </Tooltip>

              {onDismiss && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={onDismiss}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-white hover:text-slate-950 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:hover:bg-accent/80 dark:hover:text-foreground dark:hover:shadow-none dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                      aria-label="Show less like this"
                    >
                      <ThumbsDown className="h-4.5 w-4.5 stroke-[1.6]" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top">
                    Show less like this
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-row items-start justify-between gap-4 sm:gap-6">
          <div className="min-w-0 flex-1">
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-4 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
            >
              <div>
                <h3
                  className={cn(
                    'font-serif font-medium leading-tight text-slate-950 transition-colors group-hover:text-slate-700 dark:text-foreground dark:group-hover:text-foreground/92',
                    featured
                      ? 'text-2xl sm:text-[2rem]'
                      : 'text-[1.25rem] sm:text-[1.45rem]',
                  )}
                >
                  {article.title}
                </h3>
                <p
                  className={cn(
                    'mt-2 min-w-0 max-w-2xl leading-7 text-slate-600 dark:text-muted-foreground',
                    featured
                      ? 'line-clamp-3 text-base sm:text-lg'
                      : 'line-clamp-2 text-sm sm:text-[0.95rem] md:line-clamp-3',
                  )}
                >
                  {article.excerpt}
                </p>
              </div>
            </a>

            <div className="mt-4 hidden sm:block">
              <div className="flex flex-wrap gap-2">
                {article.tags?.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="border-slate-200/70 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.65)] transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 dark:border-border/85 dark:bg-card/35 dark:text-muted-foreground dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent/70 dark:hover:text-foreground"
                  >
                    {capitalize(tag)}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {article.image_url && (
            <div className="aspect-[4/3] w-24 shrink-0 overflow-hidden rounded-md bg-slate-100 sm:w-40 lg:w-48 dark:bg-muted">
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="block h-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-4 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
              >
                <img
                  src={article.image_url}
                  alt={article.title}
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                />
              </a>
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
