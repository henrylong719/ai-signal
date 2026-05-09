import { Link } from '@tanstack/react-router'
import { SlidersHorizontalIcon } from 'lucide-react'

/**
 * Soft activation prompt shown on the For-You feed when the user has
 * fewer than 3 personalization signals set.
 *
 * Threshold rationale: with 0 signals the feed degrades to recency-only,
 * with 1–2 signals the recommender has just enough to differentiate
 * articles but the user is leaving most of its capacity on the table.
 * At 3+ signals we trust the user has taken the meaningful action and
 * stop nudging them.
 *
 * No close button — the card disappears naturally when preferences
 * cross the threshold. Adding a dismissible state would create a stale
 * "I closed this once and now my feed is generic" failure mode.
 */
export function PersonalizationCard() {
  return (
    <div className="mb-6 mt-6 rounded-lg border border-slate-200/80 bg-white p-5 dark:border-border dark:bg-card/35 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-slate-50 text-slate-600 dark:border-border dark:bg-muted/35 dark:text-muted-foreground">
            <SlidersHorizontalIcon className="h-4 w-4 stroke-[1.7]" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-950 dark:text-foreground">
              Tune your signal
            </h3>
            <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
              Pick a few topics and trusted sources to make this feed yours.
            </p>
          </div>
        </div>
        <Link
          to="/personalization"
          className="inline-flex h-9 shrink-0 items-center self-start rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
        >
          Get started
        </Link>
      </div>
    </div>
  )
}
