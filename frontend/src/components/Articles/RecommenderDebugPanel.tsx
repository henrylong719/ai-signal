import { useState } from 'react'

import { cn } from '@/lib/utils'

/**
 * Per-article debug payload from the For-You endpoint when ?debug=1
 * is set by a superuser. Mirrors ``ForYouArticleDebugPublic`` /
 * ``ScoreBreakdownPublic`` on the backend; weighted contributions are
 * pre-computed server-side so the FE doesn't have to reproduce
 * ``ScoringWeights`` constants.
 *
 * Defined inline rather than imported from the generated client because
 * the OpenAPI codegen step regenerates these types from the schema —
 * keeping a local mirror lets the panel render before/after that
 * regen step. After regen you can swap this for the generated type
 * without touching anything else.
 */
export interface ScoreBreakdownDebug {
  semantic: number
  explicit: number
  source: number
  recency: number
  weighted_semantic: number
  weighted_explicit: number
  weighted_source: number
  weighted_recency: number
  total: number
  dominant_signal: string | null
}

export interface RecommenderDebugPayload {
  breakdown: ScoreBreakdownDebug
  was_exploration_injection: boolean
}

interface DebugPanelProps {
  payload: RecommenderDebugPayload
}

const SIGNAL_ROWS: Array<{
  key: 'semantic' | 'explicit' | 'source' | 'recency'
  label: string
}> = [
  { key: 'semantic', label: 'semantic' },
  { key: 'explicit', label: 'explicit' },
  { key: 'source', label: 'source' },
  { key: 'recency', label: 'recency' },
]

const formatScore = (n: number) => n.toFixed(3)

/**
 * Inline diagnostic panel for the admin recommender-debug view.
 *
 * Collapsed by default — at page-size 50 an always-expanded panel
 * dominates the actual content even for the engineer reading it.
 * Click the header to expand a single article; the parent route
 * also offers an "Expand all" affordance for cross-article
 * comparison sweeps.
 *
 * Layout choices:
 *  - Monospace numbers, four labeled rows, ``raw → weighted`` per row.
 *    Tabular alignment matters more than visual polish here.
 *  - Dominant signal gets a subtle background highlight on its row.
 *    Same logic as ``ScoreBreakdown.dominant_signal()`` on the backend,
 *    pre-computed server-side and passed verbatim.
 *  - Exploration badge sits at the top of the panel when the item was
 *    swapped in by ε-greedy injection — the breakdown alone can't tell
 *    you that, so the badge is the only signal.
 */
export function RecommenderDebugPanel({ payload }: DebugPanelProps) {
  const [expanded, setExpanded] = useState(false)
  const { breakdown, was_exploration_injection } = payload

  return (
    <div className="mt-3 rounded border border-dashed border-amber-300/60 bg-amber-50/40 text-[11px] dark:border-amber-500/30 dark:bg-amber-950/15">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-3 py-1.5 text-left font-mono text-amber-900 dark:text-amber-200/85"
        aria-expanded={expanded}
      >
        <span className="flex items-center gap-2">
          <span className="font-sans font-semibold uppercase tracking-wide">
            debug
          </span>
          {was_exploration_injection && (
            <span className="rounded bg-amber-200/70 px-1.5 py-0.5 text-[10px] font-sans font-semibold uppercase text-amber-900 dark:bg-amber-700/40 dark:text-amber-100">
              exploration
            </span>
          )}
          <span className="opacity-70">
            total={formatScore(breakdown.total)}
          </span>
          {breakdown.dominant_signal && (
            <span className="opacity-70">dom={breakdown.dominant_signal}</span>
          )}
        </span>
        <span className="font-sans text-[10px] opacity-60">
          {expanded ? '▾' : '▸'}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-amber-200/60 px-3 py-2 font-mono dark:border-amber-500/25">
          <div className="grid grid-cols-[7ch_1fr_1fr] gap-x-3 gap-y-0.5 text-amber-900 dark:text-amber-200/85">
            <div className="opacity-60">signal</div>
            <div className="opacity-60">raw</div>
            <div className="opacity-60">weighted</div>
            {SIGNAL_ROWS.map(({ key, label }) => {
              const isDominant = breakdown.dominant_signal === key
              return (
                <div
                  key={key}
                  className={cn(
                    'col-span-3 grid grid-cols-[7ch_1fr_1fr] gap-x-3 rounded-sm px-0.5',
                    isDominant && 'bg-amber-200/50 dark:bg-amber-700/30',
                  )}
                >
                  <div>{label}</div>
                  <div>{formatScore(breakdown[key])}</div>
                  <div>
                    {formatScore(
                      breakdown[
                        `weighted_${key}` as keyof ScoreBreakdownDebug
                      ] as number,
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
