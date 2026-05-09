import { CalendarIcon } from 'lucide-react'
import { DateTime } from 'luxon'
import type { DigestPublicSchema } from '@/client'

const formatDigestDate = (date: string | undefined) => {
  if (!date) {
    return DateTime.now().toLocaleString(DateTime.DATE_FULL)
  }

  const parsed = DateTime.fromISO(date)
  return parsed.isValid
    ? parsed.toLocaleString(DateTime.DATE_FULL)
    : DateTime.now().toLocaleString(DateTime.DATE_FULL)
}

const DEFAULT_INTRO =
  'The most important AI engineering updates, organized for a focused morning read.'

const buildDigestIntro = (digest: DigestPublicSchema | undefined): string => {
  if (!digest) {
    return DEFAULT_INTRO
  }

  const articleCount = digest.sections.reduce(
    (count, section) => count + section.articles.length,
    0,
  )
  // Empty digest renders the empty-state component, not this header copy —
  // but be defensive in case the header ever shows above the empty state.
  if (articleCount === 0) {
    return DEFAULT_INTRO
  }

  const cadence = articleCount === 1 ? '1 signal' : `${articleCount} signals`
  const mode = digest.is_personalized ? 'personalized' : 'curated'

  return `A ${mode} briefing of ${cadence} from today's AI research, engineering, models, and industry coverage.`
}

function DigestHeader({ digest }: { digest: DigestPublicSchema | undefined }) {
  return (
    <header className="mb-14 text-center sm:mb-16 md:mb-20">
      <div className="mb-5 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-muted-foreground">
        <CalendarIcon className="h-4 w-4 stroke-[1.5]" />
        {formatDigestDate(digest?.generated_at)}
      </div>
      <h1 className="font-serif text-4xl font-medium leading-none tracking-normal text-slate-950 sm:text-5xl md:text-6xl dark:text-foreground">
        Today's AI Signal
      </h1>
      <p className="mx-auto mt-5 max-w-2xl font-serif text-lg leading-8 text-slate-500 sm:text-xl sm:leading-9 dark:text-muted-foreground">
        {buildDigestIntro(digest)}
      </p>
    </header>
  )
}

export default DigestHeader
