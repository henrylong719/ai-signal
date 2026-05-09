import { ChevronRightIcon } from 'lucide-react'
import type { DigestArticlePublic } from '@/client'
import { redirectHref } from '@/lib/article-urls'

function DigestArticle({ article }: { article: DigestArticlePublic }) {
  const href = redirectHref(article.id)

  return (
    <article className="group py-7 sm:py-8">
      {article.reason && (
        <div className="mb-3 inline-flex rounded-full border border-stone-200 bg-stone-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-stone-700 dark:border-border dark:bg-muted/55 dark:text-muted-foreground">
          {article.reason}
        </div>
      )}

      <div className="flex items-start gap-4 sm:gap-6">
        <div className="min-w-0 flex-1">
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-4 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            <h3 className="font-serif text-[1.45rem] font-medium leading-tight tracking-normal text-slate-950 transition-colors group-hover:text-slate-700 sm:text-[1.7rem] dark:text-foreground dark:group-hover:text-foreground/82">
              {article.title}
            </h3>
          </a>

          <p className="mt-3 line-clamp-4 text-[0.96rem] leading-7 text-slate-600 sm:text-base dark:text-muted-foreground">
            {article.excerpt ?? 'No summary available yet.'}
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            <span className="font-semibold text-slate-950 dark:text-foreground">
              {article.source}
            </span>

            <span className="text-slate-300 dark:text-muted-foreground/45">
              &bull;
            </span>
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center rounded-sm text-slate-400 transition-colors hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-muted-foreground dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
            >
              Read more
              <ChevronRightIcon className="ml-0.5 h-3.5 w-3.5 stroke-2" />
            </a>
          </div>
        </div>

        {article.image_url && (
          <div className="hidden aspect-4/3 w-36 shrink-0 overflow-hidden rounded-lg bg-slate-100 sm:block md:w-44 dark:bg-muted">
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
    </article>
  )
}

export default DigestArticle
