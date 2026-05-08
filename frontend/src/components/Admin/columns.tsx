import type { ColumnDef } from '@tanstack/react-table';

import type { UserPublic } from '@/client';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { UserActionsMenu } from './UserActionsMenu';

export type UserTableData = UserPublic & {
  isCurrentUser: boolean;
};

export const columns: ColumnDef<UserTableData>[] = [
  {
    accessorKey: 'full_name',
    header: 'Full Name',
    cell: ({ row }) => {
      const fullName = row.original.full_name;
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
      );
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
    id: 'actions',
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <UserActionsMenu user={row.original} />
      </div>
    ),
  },
];
