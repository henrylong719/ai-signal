import { createFileRoute } from '@tanstack/react-router';
import { CalendarIcon, ChevronRightIcon } from 'lucide-react';
import { DateTime } from 'luxon';
import type { DigestArticlePublic, DigestPublicSchema } from '@/client';
import { Skeleton } from '@/components/ui/skeleton';
import { useTodayDigest } from '@/hooks/useTodayDigest';
import { redirectHref } from '@/lib/article-urls';

export const Route = createFileRoute('/_layout/today-digest')({
  component: TodayDigest,
  head: () => ({
    meta: [
      {
        title: "Today's AI Signal",
      },
    ],
  }),
});

const formatDigestDate = (date: string | undefined) => {
  if (!date) {
    return DateTime.now().toLocaleString(DateTime.DATE_FULL);
  }

  const parsed = DateTime.fromISO(date);
  return parsed.isValid
    ? parsed.toLocaleString(DateTime.DATE_FULL)
    : DateTime.now().toLocaleString(DateTime.DATE_FULL);
};

const digestIntro = (digest: DigestPublicSchema | undefined) => {
  if (!digest) {
    return 'The most important AI engineering updates, organized for a focused morning read.';
  }

  const articleCount = digest.sections.reduce(
    (count, section) => count + section.articles.length,
    0,
  );
  const cadence = articleCount === 1 ? '1 signal' : `${articleCount} signals`;
  const mode = digest.is_personalized ? 'personalized' : 'curated';

  return `A ${mode} briefing of ${cadence} from today's AI research, engineering, models, and industry coverage.`;
};

function TodayDigest() {
  const { data, isLoading, isError } = useTodayDigest();

  return (
    <div className="mx-auto w-full max-w-3xl py-12 sm:py-16 md:py-20">
      <header className="mb-14 text-center sm:mb-16 md:mb-20">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-muted-foreground">
          <CalendarIcon className="h-4 w-4 stroke-[1.5]" />
          {formatDigestDate(data?.generated_at)}
        </div>
        <h1 className="font-serif text-4xl font-medium leading-none tracking-normal text-slate-950 sm:text-5xl md:text-6xl dark:text-foreground">
          Today's AI Signal
        </h1>
        <p className="mx-auto mt-5 max-w-2xl font-serif text-lg leading-8 text-slate-500 sm:text-xl sm:leading-9 dark:text-muted-foreground">
          {digestIntro(data)}
        </p>
      </header>

      {/* Keep it for now, we will add emails later */}
      {/* <section className="mb-14 border-y border-slate-200/70 py-7 sm:mb-16 sm:flex sm:items-center sm:justify-between sm:gap-8 md:mb-20 dark:border-border">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 text-slate-400 dark:text-muted-foreground">
            <MailIcon className="h-4 w-4 stroke-[1.6]" />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-950 dark:text-foreground">
              Get the daily digest
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
              Email delivery is coming soon. For now, this page is your daily
              briefing.
            </p>
          </div>
        </div>
        <Button
          type="button"
          disabled
          className="mt-5 rounded-full bg-slate-950 px-5 text-sm font-medium text-white disabled:opacity-45 sm:mt-0 dark:bg-primary dark:text-primary-foreground"
        >
          Subscribe soon
        </Button>
      </section> */}

      {isLoading ? (
        <DigestSkeleton />
      ) : isError ? (
        <DigestState
          title="Could not load today's digest"
          description="Refresh the page in a moment. The digest data did not come back cleanly."
        />
      ) : !data || data.sections.length === 0 ? (
        <DigestState
          title="Today's digest will appear here"
          description="Once enough fresh articles are available, the briefing will be grouped by signal area."
        />
      ) : (
        <div className="space-y-16 md:space-y-20">
          {data.sections.map((section) => (
            <section key={section.key}>
              <div className="mb-9 flex items-center gap-4">
                <h2 className="shrink-0 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-muted-foreground">
                  {section.title}
                </h2>
                <div className="h-px flex-1 bg-slate-200/70 dark:bg-border" />
              </div>

              <div className="space-y-10 sm:space-y-12">
                {section.articles.map((article) => (
                  <DigestArticle key={article.id} article={article} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function DigestArticle({ article }: { article: DigestArticlePublic }) {
  const href = redirectHref(article.id);

  return (
    <article className="group">
      {article.reason && (
        <div className="mb-3 inline-flex rounded-full border border-stone-200 bg-stone-50 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.08em] text-stone-700 dark:border-border dark:bg-muted/55 dark:text-muted-foreground">
          {article.reason}
        </div>
      )}

      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-4 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
      >
        <h3 className="font-serif text-2xl font-medium leading-snug tracking-normal text-slate-950 transition-colors group-hover:text-slate-700 dark:text-foreground dark:group-hover:text-foreground/82">
          {article.title}
        </h3>
      </a>

      <p className="mt-3 font-serif text-lg leading-8 text-slate-600 dark:text-muted-foreground">
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
    </article>
  );
}

function DigestSkeleton() {
  return (
    <div className="space-y-16">
      {['top', 'research'].map((section) => (
        <section key={section}>
          <div className="mb-9 flex items-center gap-4">
            <Skeleton className="h-3 w-24 rounded bg-slate-100 dark:bg-muted" />
            <Skeleton className="h-px flex-1 rounded bg-slate-100 dark:bg-muted" />
          </div>
          <div className="space-y-12">
            {['a', 'b'].map((item) => (
              <div key={item}>
                <Skeleton className="h-7 w-11/12 rounded bg-slate-100 dark:bg-muted" />
                <Skeleton className="mt-4 h-5 w-full rounded bg-slate-100 dark:bg-muted" />
                <Skeleton className="mt-2 h-5 w-4/5 rounded bg-slate-100 dark:bg-muted" />
                <Skeleton className="mt-5 h-4 w-48 rounded bg-slate-100 dark:bg-muted" />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function DigestState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200/80 bg-white px-6 py-10 text-center dark:border-border dark:bg-card/35">
      <h2 className="font-serif text-2xl font-medium text-slate-950 dark:text-foreground">
        {title}
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500 dark:text-muted-foreground">
        {description}
      </p>
    </div>
  );
}
