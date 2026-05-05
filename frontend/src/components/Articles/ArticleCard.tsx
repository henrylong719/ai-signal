import { BookmarkIcon, ThumbsDown } from "lucide-react"
import { DateTime } from "luxon"
import type { ArticlePublic } from "@/client"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { isLoggedIn } from "@/hooks/useAuth"
import { redirectHref } from "@/lib/article-urls"
import { capitalize, cn } from "@/lib/utils"
import { Badge } from "../ui/badge"

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
    <div
      className={cn(
        "group flex flex-col gap-4 py-8 border-b border-slate-100 last:border-0",
        className,
      )}
    >
      <div className="flex flex-col gap-3">
        {reason && (
          <div className="text-xs font-sans uppercase tracking-wide text-slate-400">
            {reason}
          </div>
        )}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-sans">
            <span className="text-slate-900">{article.source}</span>
            <span className="text-slate-300">&bull;</span>
            <span>
              {article.published_at
                ? DateTime.fromISO(article.published_at).toLocaleString(
                    DateTime.DATE_MED,
                  )
                : ""}
            </span>
          </div>
          {showActions && (
            <div className="-mr-1 flex shrink-0 items-center gap-1 text-slate-400">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={onBookmark}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
                    aria-label={
                      isBookmarked ? "Remove saved article" : "Save article"
                    }
                    aria-pressed={isBookmarked}
                  >
                    <BookmarkIcon
                      className={cn(
                        "h-4.5 w-4.5 stroke-[1.6]",
                        isBookmarked && "fill-slate-900 text-slate-900",
                      )}
                    />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top">
                  {isBookmarked ? "Remove saved article" : "Save article"}
                </TooltipContent>
              </Tooltip>

              {onDismiss && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={onDismiss}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
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

        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="flex flex-col justify-between md:h-40 md:flex-3">
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
            >
              <div>
                <h3
                  className={cn(
                    "font-serif font-medium text-slate-900 group-hover:text-slate-600 transition-colors leading-snug",
                    featured ? "text-3xl" : "text-xl",
                  )}
                >
                  {article.title}
                </h3>
                <p
                  className={cn(
                    "min-w-0 flex-1 text-slate-500 font-serif leading-relaxed",
                    featured ? "text-lg mt-1" : "text-base line-clamp-3",
                  )}
                >
                  {article.excerpt}
                </p>
              </div>
            </a>

            <div className="mt-3">
              <div className="flex flex-wrap gap-2">
                {article.tags?.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="font-sans font-normal text-xs text-slate-600 bg-slate-100 border-transparent hover:bg-slate-200 px-2 py-0.5 cursor-pointer"
                  >
                    {capitalize(tag)}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {article.image_url && (
            <div className="aspect-16/10 w-full shrink-0 overflow-hidden rounded-sm md:flex-1">
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="block h-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
              >
                <img
                  src={article.image_url}
                  alt={article.title}
                  className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                />
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
