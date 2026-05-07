import { useQueryClient, useSuspenseQuery } from '@tanstack/react-query';
import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { Suspense, useState } from 'react';

import { AdminService } from '@/client';
import { ingestRunColumns } from '@/components/Admin/ingestRunColumns';
import { DataTable } from '@/components/Common/DataTable';
import PendingIngestRuns from '@/components/Pending/PendingIngestRuns';
import { Button } from '@/components/ui/button';
import useCustomToast from '@/hooks/useCustomToast';
import { cn } from '@/lib/utils';

/**
 * Admin page for ingestion run history.
 *
 * Powers the "is the cron healthy?" question. Lists the most recent 50
 * runs with status, counts, duration, and any errors. Refresh-on-click
 * is the only interactivity in this round — auto-refresh would be the
 * obvious next polish step but is gated on watching real runs first
 * and finding out we actually want it.
 */

function getIngestRunsQueryOptions() {
  return {
    queryFn: () => AdminService.readIngestRuns({ limit: 50 }),
    queryKey: ['ingest-runs'],
  };
}

export const Route = createFileRoute('/_layout/admin/ingest-runs')({
  component: IngestRunsPage,
  head: () => ({
    meta: [
      {
        title: 'Ingest Runs - Admin',
      },
    ],
  }),
});

function IngestRunsTableContent() {
  const { data } = useSuspenseQuery(getIngestRunsQueryOptions());
  return <DataTable columns={ingestRunColumns} data={data.data} />;
}

function IngestRunsTable() {
  return (
    <Suspense fallback={<PendingIngestRuns />}>
      <IngestRunsTableContent />
    </Suspense>
  );
}

function IngestRunsPage() {
  const queryClient = useQueryClient();
  const { showSuccessToast, showErrorToast } = useCustomToast();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    if (isRefreshing) {
      return;
    }

    setIsRefreshing(true);

    try {
      await queryClient.invalidateQueries({ queryKey: ['ingest-runs'] });
      showSuccessToast('Ingest runs refreshed.');
    } catch {
      showErrorToast('Could not refresh ingest runs. Try again.');
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 pb-16 pt-8 sm:pb-20 sm:pt-10">
      <header className="flex flex-col gap-4 border-b border-slate-200/70 pb-6 sm:flex-row sm:items-end sm:justify-between dark:border-border">
        <div>
          <Link
            to="/admin"
            className="mb-3 inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 transition-colors hover:text-slate-600 dark:text-muted-foreground dark:hover:text-foreground"
          >
            <ArrowLeft className="size-3" />
            Admin
          </Link>
          <h1 className="font-display text-3xl font-semibold tracking-normal text-slate-950 sm:text-4xl dark:text-foreground">
            Ingest Runs
          </h1>
          <p className="mt-3 max-w-xl text-base leading-7 text-slate-500 dark:text-muted-foreground">
            Recent ingestion runs from the scheduled cron and any manual
            triggers. The 50 most recent runs are shown.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
          aria-busy={isRefreshing}
          className="gap-2"
        >
          <RefreshCw
            className={cn('size-3.5', isRefreshing && 'animate-spin')}
          />
          {isRefreshing ? 'Refreshing' : 'Refresh'}
        </Button>
      </header>
      <IngestRunsTable />
    </div>
  );
}
