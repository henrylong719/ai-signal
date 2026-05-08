import { Link } from '@tanstack/react-router'
import { CalendarIcon, ChevronRightIcon } from 'lucide-react'
import { useMemo } from 'react'
import type { DigestArticlePublic, DigestSectionPublic } from '@/client'
import { Skeleton } from '@/components/ui/skeleton'
import { useTodayDigest } from '@/hooks/useTodayDigest'
import { redirectHref } from '@/lib/article-urls'

const getSourceKey = (source: string) => source.trim().toLowerCase()

const getPreviewArticles = (
  sections: DigestSectionPublic[] | undefined,
): DigestArticlePublic[] => {
  const articles = sections?.flatMap((section) => section.articles) ?? []
  const selected: DigestArticlePublic[] = []
  const seenSources = new Set<string>()

  for (const article of articles) {
    const sourceKey = getSourceKey(article.source)

    if (seenSources.has(sourceKey)) {
      continue
    }

    selected.push(article)
    seenSources.add(sourceKey)

    if (selected.length >= 3) {
      return selected
    }
  }

  return selected
}

const TodayDigest = () => {
  const { data, isLoading, isError } = useTodayDigest()

  const articles = useMemo(
    () => getPreviewArticles(data?.sections),
    [data?.sections],
  )

  return (
    <div>
      <div className="mb-3 flex items-center gap-2.5 lg:mb-4">
        <div className="text-slate-400 dark:text-muted-foreground">
          <CalendarIcon className="h-4 w-4 stroke-[1.6]" />
        </div>
        <span className="text-sm font-semibold text-slate-500 dark:text-muted-foreground">
          Today's Digest
        </span>
      </div>
      <div className="mt-2 space-y-3 lg:space-y-5">
        {isLoading ? (
          ['a', 'b', 'c'].map((key, index) => (
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
          ))
        ) : isError ? (
          <p className="rounded-lg border border-slate-100 bg-white p-3 text-sm text-slate-500 dark:border-border dark:bg-card/45 dark:text-muted-foreground">
            Could not load today's digest.
          </p>
        ) : articles.length === 0 ? (
          <p className="rounded-lg border border-slate-100 bg-white p-3 text-sm text-slate-500 dark:border-border dark:bg-card/45 dark:text-muted-foreground">
            Today's digest will appear here.
          </p>
        ) : (
          articles.map((article, index) => (
            <div
              key={article.id}
              className={`group flex items-start gap-3 lg:gap-4 ${
                index === 2 ? 'hidden lg:flex' : ''
              }`}
            >
              <div className="min-w-0">
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
  )
}

export default TodayDigest
