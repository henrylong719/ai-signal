import { BookmarkIcon, XIcon } from 'lucide-react';
import { DateTime } from 'luxon';
import type { ArticlePublic } from '@/client';
import { isLoggedIn } from '@/hooks/useAuth';
import { redirectHref } from '@/lib/article-urls';
import { capitalize, cn } from '@/lib/utils';
import { Badge } from '../ui/badge';

interface ArticleCardProps {
  article: ArticlePublic;
  featured?: boolean;
  className?: string;
  onBookmark?: (e: React.MouseEvent) => void;
  isBookmarked?: boolean;
  /**
   * If provided, renders a dismiss button next to the bookmark.
   * The For-You feed wires this; other feeds (Latest, Saved, etc.) leave
   * it unset, so the button is hidden.
   */
  onDismiss?: (e: React.MouseEvent) => void;
}

export function ArticleCard({
  article,
  featured = false,
  className,
  onBookmark,
  isBookmarked = false,
  onDismiss,
}: ArticleCardProps) {
  // Outbound links go through our redirect endpoint so we can record
  // the click as a behavioral signal for the recommender. Cookie auth
  // makes this work — the browser sends the access cookie on the
  // navigation. See lib/article-urls.ts for details.
  const href = redirectHref(article.id);

  return (
    <div
      className={cn(
        'group flex flex-col gap-4 py-8 border-b border-slate-100 last:border-0',
        className,
      )}
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-sans">
            <span className="text-slate-900">{article.source}</span>
            <span className="text-slate-300">&bull;</span>
            <span>
              {article.published_at
                ? DateTime.fromISO(article.published_at).toLocaleString(
                    DateTime.DATE_MED,
                  )
                : ''}
            </span>
          </div>
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
                    'font-serif font-medium text-slate-900 group-hover:text-slate-600 transition-colors leading-snug',
                    featured ? 'text-3xl' : 'text-xl',
                  )}
                >
                  {article.title}
                </h3>
                <p
                  className={cn(
                    'min-w-0 flex-1 text-slate-500 font-serif leading-relaxed',
                    featured ? 'text-lg mt-1' : 'text-base line-clamp-3',
                  )}
                >
                  {article.excerpt}
                </p>
              </div>
            </a>

            <div className="mt-3 flex items-center justify-between">
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
              {isLoggedIn() && (
                <div className="flex items-center gap-1 shrink-0">
                  {onDismiss && (
                    <button
                      type="button"
                      onClick={onDismiss}
                      className="rounded-full p-1 text-slate-300 transition-colors hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
                      aria-label="Not interested in this article"
                    >
                      <XIcon className="w-5 h-5 stroke-[1.5]" />
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={onBookmark}
                    className="rounded-full p-1 text-slate-300 transition-colors hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
                    aria-label={
                      isBookmarked ? 'Remove saved article' : 'Save article'
                    }
                    aria-pressed={isBookmarked}
                  >
                    <BookmarkIcon
                      className={cn(
                        'w-5 h-5 stroke-[1.5]',
                        isBookmarked && 'fill-slate-900 text-slate-900',
                      )}
                    />
                  </button>
                </div>
              )}
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
  );
}
