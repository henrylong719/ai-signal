import { Link } from '@tanstack/react-router';
import { CalendarIcon, ChevronRightIcon } from 'lucide-react';
import { DateTime } from 'luxon';
import type { DigestArticlePublic, DigestSectionPublic } from '@/client';
import { Skeleton } from '@/components/ui/skeleton';
import { useTodayDigest } from '@/hooks/useTodayDigest';
import { redirectHref } from '@/lib/article-urls';

const PREVIEW_LIMIT = 3;

// The backend's digest already builds a "Top stories" section with
// distinct-source preference (see services/digest._top_stories). The
// landing preview is just the head of that section — no need to
// re-flatten and re-deduplicate here.
const getPreviewArticles = (
  sections: DigestSectionPublic[] | undefined,
): DigestArticlePublic[] => {
  const top = sections?.find((section) => section.key === 'top');
  return top?.articles.slice(0, PREVIEW_LIMIT) ?? [];
};

const TodayDigestSkeleton = () => (
  <>
    {['a', 'b', 'c'].map((key, index) => (
      <div
        key={key}
        className={`flex items-start gap-3 lg:gap-4 ${
          index === 2 ? 'hidden lg:flex' : ''
        }`}
      >
        <Skeleton className="h-8 w-6 rounded bg-slate-100 dark:bg-muted" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-full rounded bg-slate-100 dark:bg-muted" />
          <Skeleton className="h-3 w-24 rounded bg-slate-100 dark:bg-muted" />
        </div>
      </div>
    ))}
  </>
);

const TodayDigestMessage = ({ children }: { children: React.ReactNode }) => (
  <p className="rounded-lg border border-slate-100 bg-white p-3 text-sm text-slate-500 dark:border-border dark:bg-card/45 dark:text-muted-foreground">
    {children}
  </p>
);

const TodayDigestPreviewItem = ({
  article,
  hideOnSmall,
}: {
  article: DigestArticlePublic;
  hideOnSmall: boolean;
}) => (
  <div
    className={`group flex items-start gap-3 lg:gap-4 ${
      hideOnSmall ? 'hidden lg:flex' : ''
    }`}
  >
    <div className="min-w-0 flex-1">
      <a
        href={redirectHref(article.id)}
        target="_blank"
        rel="noreferrer"
        className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
      >
        <h4 className="mb-1 line-clamp-2 text-[0.9375rem] font-medium leading-6 text-slate-950 transition-colors group-hover:text-slate-700 lg:mb-1.5 lg:line-clamp-none lg:font-serif lg:text-base lg:leading-snug dark:text-foreground dark:group-hover:text-foreground/78">
          {article.title}
        </h4>
      </a>
      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        <span className="text-slate-600 dark:text-muted-foreground">
          {article.source}
        </span>
      </div>
    </div>
  </div>
);

const TodayDigest = () => {
  const { data, isLoading, isError } = useTodayDigest();
  const articles = getPreviewArticles(data?.sections);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-x-2.5 gap-y-1 lg:mb-4">
        <div className="flex items-center gap-2.5">
          <div className="text-slate-400 dark:text-muted-foreground">
            <CalendarIcon className="h-4 w-4 stroke-[1.6]" />
          </div>
          <span className="text-sm font-semibold text-slate-500 dark:text-muted-foreground">
            Today's Digest
          </span>
        </div>
        {data?.generated_at && articles.length > 0 ? (
          <span className="text-[11px] font-medium text-slate-400 dark:text-muted-foreground/75">
            Updated {DateTime.fromISO(data.generated_at).toRelative()}
          </span>
        ) : null}
      </div>
      <div className="mt-2 space-y-3 lg:space-y-5">
        {isLoading ? (
          <TodayDigestSkeleton />
        ) : isError ? (
          <TodayDigestMessage>
            Could not load today's digest.
          </TodayDigestMessage>
        ) : articles.length === 0 ? (
          <TodayDigestMessage>
            Today's digest is still being assembled. Check back later — we group
            the day's most important AI updates by signal area.
          </TodayDigestMessage>
        ) : (
          articles.map((article, index) => (
            <TodayDigestPreviewItem
              key={article.id}
              article={article}
              hideOnSmall={index === 2}
            />
          ))
        )}
      </div>

      <Link
        to="/today-digest"
        className="mt-3 inline-flex items-center rounded-sm text-xs font-semibold text-slate-500 transition-colors hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 lg:mt-4 dark:text-muted-foreground dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
      >
        Read all daily digests
        <ChevronRightIcon className="w-3 h-3 ml-0.5 stroke-2" />
      </Link>
    </div>
  );
};

export default TodayDigest;
