import { createFileRoute } from '@tanstack/react-router'
import { CalendarIcon } from 'lucide-react'
import { DateTime } from 'luxon'
import type { DigestPublicSchema } from '@/client'
import DigestArticle from '@/components/Digest/DigestArticle'
import DigestSkeleton from '@/components/Digest/DigestSkeleton'
import DigestState from '@/components/Digest/DigestState'
import { PageContainer } from '@/components/Layout/Page'
import { useTodayDigest } from '@/hooks/useTodayDigest'

export const Route = createFileRoute('/_layout/today-digest')({
  component: TodayDigest,
  head: () => ({
    meta: [
      {
        title: "Today's AI Signal",
      },
    ],
  }),
})

const formatDigestDate = (date: string | undefined) => {
  if (!date) {
    return DateTime.now().toLocaleString(DateTime.DATE_FULL)
  }

  const parsed = DateTime.fromISO(date)
  return parsed.isValid
    ? parsed.toLocaleString(DateTime.DATE_FULL)
    : DateTime.now().toLocaleString(DateTime.DATE_FULL)
}

const digestIntro = (digest: DigestPublicSchema | undefined) => {
  if (!digest) {
    return 'The most important AI engineering updates, organized for a focused morning read.'
  }

  const articleCount = digest.sections.reduce(
    (count, section) => count + section.articles.length,
    0,
  )
  const cadence = articleCount === 1 ? '1 signal' : `${articleCount} signals`
  const mode = digest.is_personalized ? 'personalized' : 'curated'

  return `A ${mode} briefing of ${cadence} from today's AI research, engineering, models, and industry coverage.`
}

function TodayDigest() {
  const { data, isLoading, isError } = useTodayDigest()

  return (
    <PageContainer
      variant="narrow"
      spacing="none"
      className="max-w-3xl py-12 sm:py-16 md:py-20"
    >
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
    </PageContainer>
  )
}
