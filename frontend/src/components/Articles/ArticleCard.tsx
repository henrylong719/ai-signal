import { Link } from "@tanstack/react-router"
import { BookmarkIcon } from "lucide-react"
import { DateTime } from "luxon"
import type { ArticlePublic } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"
import { capitalize, cn } from "@/lib/utils"
import { Badge } from "../ui/badge"

interface ArticleCardProps {
  article: ArticlePublic
  featured?: boolean
  className?: string
  onBookmark?: (e: React.MouseEvent) => void
  isBookmarked?: boolean
}

/**
 * Decide what body text to show in the card.
 *
 * Priority:
 *   1. The LLM-written summary, if enrichment succeeded.
 *   2. A "generating..." placeholder while enrichment is pending.
 *   3. The raw RSS excerpt as a fallback (skipped/failed rows, or
 *      enriched rows with no summary for some reason).
 *
 * Returning `{ text, italic }` lets the caller style the placeholder
 * subtly differently from real content.
 */
function getCardBody(
  article: ArticlePublic,
): { text: string; italic: boolean } | null {
  if (article.summary_status === "done" && article.summary) {
    return { text: article.summary, italic: false }
  }
  if (article.summary_status === "pending") {
    return { text: "Generating summary…", italic: true }
  }
  // "skipped" (title_only / insufficient) and "failed" fall through here.
  if (article.excerpt) {
    return { text: article.excerpt, italic: false }
  }
  return null
}

const DIFFICULTY_LABEL: Record<
  NonNullable<ArticlePublic["difficulty"]>,
  string
> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
}

export function ArticleCard({
  article,
  featured = false,
  className,
  onBookmark,
  isBookmarked = false,
}: ArticleCardProps) {
  const body = getCardBody(article)
  const publishedDate = article.published_at
    ? DateTime.fromISO(article.published_at).toLocaleString(DateTime.DATE_MED)
    : null
  const canBookmark = isLoggedIn() && onBookmark

  return (
    <article
      className={cn(
        "group border-b border-slate-100 py-5 last:border-0 sm:py-6",
        className,
      )}
    >
      <div
        className={cn(
          "grid gap-4 rounded-md p-3 transition-colors hover:bg-slate-50/80 sm:p-4",
          article.image_url &&
            "md:grid-cols-[minmax(0,1fr)_13rem] md:gap-5 lg:grid-cols-[minmax(0,1fr)_16rem]",
        )}
      >
        <div className="min-w-0 space-y-3.5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 font-sans text-xs text-slate-500">
              <span className="max-w-full truncate font-medium text-slate-900">
                {article.source}
              </span>
              {publishedDate && (
                <>
                  <span className="text-slate-300">&bull;</span>
                  <span>{publishedDate}</span>
                </>
              )}
            </div>

            {canBookmark && (
              <button
                type="button"
                onClick={onBookmark}
                className="shrink-0 rounded-full p-1.5 text-slate-300 transition-colors hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
                aria-label={
                  isBookmarked ? "Remove saved article" : "Save article"
                }
                aria-pressed={isBookmarked}
              >
                <BookmarkIcon
                  className={cn(
                    "h-5 w-5 stroke-[1.5]",
                    isBookmarked && "fill-slate-900 text-slate-900",
                  )}
                />
              </button>
            )}
          </div>

          <Link
            to={article.url}
            target="_blank"
            rel="noreferrer"
            className="block rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
          >
            <h3
              className={cn(
                "font-serif font-medium leading-tight text-slate-950 transition-colors group-hover:text-slate-700",
                featured ? "text-3xl" : "text-xl sm:text-2xl",
              )}
            >
              {article.title}
            </h3>
          </Link>

          {body && (
            <p
              className={cn(
                "min-w-0 text-pretty font-serif leading-relaxed text-slate-600",
                featured ? "text-lg" : "line-clamp-2 text-base",
                body.italic && "italic text-slate-400",
              )}
            >
              {body.text}
            </p>
          )}

          {article.why_it_matters && (
            <div className="border-l-2 border-slate-200 pl-3">
              <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                Why it matters
              </span>
              <p
                className={cn(
                  "mt-1 font-serif leading-relaxed text-slate-700",
                  featured ? "text-base" : "line-clamp-2 text-sm",
                )}
              >
                {article.why_it_matters}
              </p>
            </div>
          )}
        </div>

        {article.image_url && (
          <Link
            to={article.url}
            target="_blank"
            rel="noreferrer"
            className="order-first block aspect-[16/10] overflow-hidden rounded-md border border-slate-100 bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 md:order-none md:self-start"
          >
            <img
              src={article.image_url}
              alt={article.title}
              className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
            />
          </Link>
        )}

        <div className="flex flex-wrap items-center gap-2 md:col-start-1">
          {article.difficulty && (
            <Badge
              variant="outline"
              className="border-slate-200 bg-white px-2.5 py-0.5 font-sans text-xs font-normal text-slate-600"
            >
              {DIFFICULTY_LABEL[article.difficulty]}
            </Badge>
          )}
          {article.tags?.map((tag) => (
            <Badge
              key={tag}
              variant="secondary"
              className="cursor-pointer border-transparent bg-slate-100 px-2.5 py-0.5 font-sans text-xs font-normal text-slate-600 hover:bg-slate-200"
            >
              {capitalize(tag)}
            </Badge>
          ))}
        </div>
      </div>
    </article>
  )
}
