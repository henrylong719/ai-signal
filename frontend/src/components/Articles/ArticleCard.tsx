import type { ArticlePublic } from '@/client';
import { Badge } from '../ui/badge';
import { BookmarkIcon } from 'lucide-react';
import { Link } from '@tanstack/react-router';
import { cn } from '@/lib/utils';

interface ArticleCardProps {
  article: ArticlePublic;
  featured?: boolean;
  className?: string;
  onBookmark?: (e: React.MouseEvent) => void;
  isBookmarked?: boolean;
}

export function ArticleCard({
  article,
  featured = false,
  className,
  onBookmark,
  isBookmarked = false,
}: ArticleCardProps) {
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
            <span>{article.published_at}</span>
            <span className="text-slate-300">&bull;</span>
          </div>
        </div>

        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="flex flex-col justify-between md:h-50 md:flex-3">
            <Link to={article.url} target="_blank">
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
            </Link>

            <div className="mt-3 flex items-center justify-between">
              <div className="flex flex-wrap gap-2">
                {article.tags?.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="font-sans font-normal text-xs text-slate-500 bg-slate-50 border-transparent hover:bg-slate-100 px-2 py-0.5"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
              <button
                type="button"
                onClick={onBookmark}
                className="text-slate-300 hover:text-slate-900 transition-colors"
                aria-label="Save article"
              >
                <BookmarkIcon
                  className={cn(
                    'w-5 h-5 stroke-[1.5]',
                    isBookmarked && 'fill-slate-900 text-slate-900',
                  )}
                />
              </button>
            </div>
          </div>

          {article.image_url && (
            <div className="aspect-16/10 w-full shrink-0 overflow-hidden rounded-sm md:flex-1">
              <Link to={article.url} target="_blank" className="block h-full">
                <img
                  src={article.image_url}
                  alt={article.title}
                  className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                />
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
