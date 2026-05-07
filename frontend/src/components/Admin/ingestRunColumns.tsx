import type { ColumnDef } from '@tanstack/react-table'
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'

import type { IngestRunPublic } from '@/client'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const STALE_RUN_ERROR = 'process terminated before completion'

/**
 * Column definitions for the ingest-runs admin table.
 *
 * The columns are ordered so the most operationally important info is
 * leftmost: when the run happened, what its outcome was, and how
 * long it took. Counts and errors trail because operators usually
 * scan the status column first.
 */
export const ingestRunColumns: ColumnDef<IngestRunPublic>[] = [
  {
    accessorKey: 'started_at',
    header: 'Started',
    cell: ({ row }) => (
      <span className="font-mono text-xs text-muted-foreground">
        {formatTimestamp(row.original.started_at)}
      </span>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge run={row.original} />,
  },
  {
    accessorKey: 'duration_ms',
    header: 'Duration',
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {isAbandonedRun(row.original)
          ? 'Unknown'
          : formatDuration(row.original.duration_ms)}
      </span>
    ),
  },
  {
    accessorKey: 'inserted',
    header: 'Inserted',
    cell: ({ row }) => (
      <span className="font-medium tabular-nums">{row.original.inserted}</span>
    ),
  },
  {
    accessorKey: 'skipped',
    header: 'Skipped',
    cell: ({ row }) => (
      <span className="tabular-nums text-muted-foreground">
        {row.original.skipped}
      </span>
    ),
  },
  {
    accessorKey: 'embedded',
    header: 'Embedded',
    cell: ({ row }) => (
      <span className="tabular-nums text-muted-foreground">
        {row.original.embedded}
      </span>
    ),
  },
  {
    accessorKey: 'errors',
    header: 'Errors',
    cell: ({ row }) => {
      const errors = row.original.errors
      if (isAbandonedRun(row.original)) {
        return (
          <span
            className="line-clamp-1 max-w-[28ch] text-xs text-amber-700 dark:text-amber-300/85"
            title="Run was last seen running and marked failed by a later ingest."
          >
            Last seen running; marked failed later
          </span>
        )
      }
      if (errors.length === 0) {
        return <span className="text-muted-foreground">—</span>
      }
      // Show first error inline; full list on hover via title attribute.
      // A modal or expand-row would be the next polish step but is
      // deferred — when there are 2+ errors per run we'll know it
      // matters because we'll actually be looking at this column.
      return (
        <span
          className="line-clamp-1 max-w-[28ch] text-xs text-amber-700 dark:text-amber-300/85"
          title={errors.join('\n')}
        >
          {errors.length > 1
            ? `${errors[0]} (+${errors.length - 1} more)`
            : errors[0]}
        </span>
      )
    },
  },
]

function StatusBadge({ run }: { run: IngestRunPublic }) {
  if (isAbandonedRun(run)) {
    return (
      <Badge
        variant="outline"
        className={cn(
          'gap-1.5 border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-300',
        )}
      >
        <AlertCircle className="size-3" />
        Abandoned
      </Badge>
    )
  }
  if (run.status === 'running') {
    return (
      <Badge variant="outline" className="gap-1.5">
        <Loader2 className="size-3 animate-spin" />
        Running
      </Badge>
    )
  }
  if (run.status === 'succeeded') {
    return (
      <Badge
        variant="outline"
        className="gap-1.5 border-green-200 bg-green-50 text-green-800 dark:border-green-400/20 dark:bg-green-400/10 dark:text-green-300"
      >
        <CheckCircle2 className="size-3" />
        Succeeded
      </Badge>
    )
  }
  return (
    <Badge
      variant="outline"
      className={cn(
        'gap-1.5 border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-300',
      )}
    >
      <AlertCircle className="size-3" />
      Failed
    </Badge>
  )
}

function isAbandonedRun(run: IngestRunPublic): boolean {
  return run.status === 'failed' && run.errors.includes(STALE_RUN_ERROR)
}

/**
 * Render an ISO-8601 timestamp as a human-friendly local time.
 *
 * Format chosen so the value is sortable when read top-to-bottom:
 * "May 06, 14:32:05" instead of a relative "5 minutes ago" — the
 * latter looks friendlier but is harder to correlate with logs or
 * with adjacent rows.
 */
function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

/**
 * Render a duration in milliseconds as ``Ns`` or ``N.Ns``.
 *
 * Null/undefined renders as an em-dash because a running row legitimately
 * has no duration yet — distinguishing "in flight" from "0ms" matters.
 */
function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) {
    return '—'
  }
  if (ms < 1000) {
    return `${ms}ms`
  }
  const seconds = ms / 1000
  if (seconds < 60) {
    // One decimal for sub-minute durations so the visual difference
    // between a 12-second run and a 32-second run is legible.
    return `${seconds.toFixed(1)}s`
  }
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.floor(seconds % 60)
  return `${minutes}m ${remainder}s`
}
