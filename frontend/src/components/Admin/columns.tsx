import type { ColumnDef } from '@tanstack/react-table'

import type { UserPublic } from '@/client'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { UserActionsMenu } from './UserActionsMenu'

export type UserTableData = UserPublic & {
  isCurrentUser: boolean
}

// Coarse "Last seen" label. Buckets are deliberately fuzzy because the
// backend throttles writes to a 5-minute window — finer granularity
// would imply a precision the data doesn't have.
function formatRelativeLastSeen(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return '—'
  const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000))
  if (diffSec < 60) return 'just now'
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 30) return `${diffDay}d ago`
  const diffMonth = Math.floor(diffDay / 30)
  if (diffMonth < 12) return `${diffMonth}mo ago`
  return `${Math.floor(diffMonth / 12)}y ago`
}

function formatExactTimestamp(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export const columns: ColumnDef<UserTableData>[] = [
  {
    accessorKey: 'full_name',
    header: 'Full Name',
    cell: ({ row }) => {
      const fullName = row.original.full_name
      return (
        <div className="flex items-center gap-2">
          <span
            className={cn('font-medium', !fullName && 'text-muted-foreground')}
          >
            {fullName || 'N/A'}
          </span>
          {row.original.isCurrentUser && (
            <Badge variant="outline" className="text-xs">
              You
            </Badge>
          )}
        </div>
      )
    },
  },
  {
    accessorKey: 'email',
    header: 'Email',
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.original.email}</span>
    ),
  },
  {
    accessorKey: 'is_superuser',
    header: 'Role',
    cell: ({ row }) => (
      <Badge
        variant={row.original.is_superuser ? 'outline' : 'secondary'}
        className={
          row.original.is_superuser
            ? 'border-slate-200 bg-slate-50 text-slate-700 dark:border-border dark:bg-muted/20 dark:text-foreground/86'
            : undefined
        }
      >
        {row.original.is_superuser ? 'Superuser' : 'User'}
      </Badge>
    ),
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <span
          className={cn(
            'size-2 rounded-full',
            row.original.is_active
              ? 'bg-emerald-500/85 dark:bg-primary'
              : 'bg-slate-300 dark:bg-muted-foreground/45',
          )}
        />
        <span className={row.original.is_active ? '' : 'text-muted-foreground'}>
          {row.original.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>
    ),
  },
  {
    accessorKey: 'last_seen_at',
    header: 'Last seen',
    cell: ({ row }) => {
      const lastSeen = row.original.last_seen_at
      if (!lastSeen) {
        return <span className="text-muted-foreground">Never</span>
      }
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="text-muted-foreground cursor-default">
              {formatRelativeLastSeen(lastSeen)}
            </span>
          </TooltipTrigger>
          <TooltipContent>{formatExactTimestamp(lastSeen)}</TooltipContent>
        </Tooltip>
      )
    },
  },
  {
    id: 'actions',
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <UserActionsMenu user={row.original} />
      </div>
    ),
  },
]
