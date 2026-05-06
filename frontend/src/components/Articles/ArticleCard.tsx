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
        "group flex flex-col gap-4 border-b border-slate-100 py-6 last:border-0 sm:py-8",
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

        <div className="flex flex-row items-start justify-between gap-4 md:gap-6">
          <div className="min-w-0 flex-1 md:flex md:h-40 md:flex-3 md:flex-col md:justify-between">
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
            >
              <div>
                <h3
                  className={cn(
                    "font-serif font-medium leading-snug text-slate-900 transition-colors group-hover:text-slate-600",
                    featured ? "text-2xl sm:text-3xl" : "text-lg sm:text-xl",
                  )}
                >
                  {article.title}
                </h3>
                <p
                  className={cn(
                    "min-w-0 flex-1 font-serif leading-relaxed text-slate-500",
                    featured
                      ? "mt-1 line-clamp-3 text-base sm:text-lg"
                      : "line-clamp-2 text-sm sm:text-base md:line-clamp-3",
                  )}
                >
                  {article.excerpt}
                </p>
              </div>
            </a>

            <div className="mt-3 hidden sm:block">
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
            <div className="aspect-4/3 w-28 shrink-0 overflow-hidden rounded-sm sm:w-36 md:aspect-16/10 md:w-full md:flex-1">
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
