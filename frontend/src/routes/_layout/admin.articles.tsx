import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import type { PaginationState } from '@tanstack/react-table'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { useState } from 'react'

import { AdminService } from '@/client'
import { articleColumns } from '@/components/Admin/articleColumns'
import { DataTable } from '@/components/Common/DataTable'
import { PageContainer, PageHeader } from '@/components/Layout/Page'
import PendingArticles from '@/components/Pending/PendingArticles'
import { Button } from '@/components/ui/button'
import useCustomToast from '@/hooks/useCustomToast'
import { cn } from '@/lib/utils'

const DEFAULT_PAGE_SIZE = 50

function adminArticlesQueryKey(pagination: PaginationState) {
  return [
    'admin-articles',
    {
      skip: pagination.pageIndex * pagination.pageSize,
      limit: pagination.pageSize,
    },
  ] as const
}

export const Route = createFileRoute('/_layout/admin/articles')({
  component: AdminArticlesPage,
  head: () => ({
    meta: [
      {
        title: 'Articles - Admin',
      },
    ],
  }),
})

function AdminArticlesPage() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  })

  const { data, isLoading, isError } = useQuery({
    queryKey: adminArticlesQueryKey(pagination),
    queryFn: () =>
      AdminService.readAdminArticles({
        skip: pagination.pageIndex * pagination.pageSize,
        limit: pagination.pageSize,
      }),
    placeholderData: keepPreviousData,
  })

  const handleRefresh = async () => {
    if (isRefreshing) {
      return
    }

    setIsRefreshing(true)

    try {
      await queryClient.invalidateQueries({ queryKey: ['admin-articles'] })
      showSuccessToast('Articles refreshed.')
    } catch {
      showErrorToast('Could not refresh articles. Try again.')
    } finally {
      setIsRefreshing(false)
    }
  }

  const rows = data?.data ?? []
  const total = data?.count ?? 0
  const pageCount = Math.max(1, Math.ceil(total / pagination.pageSize))

  return (
    <PageContainer
      variant="default"
      spacing="compact"
      className="flex flex-col gap-6"
    >
      <PageHeader
        className="mb-0 border-slate-200/70 pb-6"
        eyebrow={
          <Link
            to="/admin"
            className="mb-3 inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 transition-colors hover:text-slate-600 dark:text-muted-foreground dark:hover:text-foreground"
          >
            <ArrowLeft className="size-3" />
            Admin
          </Link>
        }
        eyebrowClassName="mb-3"
        title="Articles"
        titleClassName="tracking-normal"
        description="Review every article in the database and permanently delete rows that should not stay in circulation."
        descriptionClassName="max-w-xl"
        actions={
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
        }
      />
      {isLoading && !data ? (
        <PendingArticles />
      ) : isError ? (
        <p className="text-sm text-muted-foreground">
          Could not load articles. Try refreshing.
        </p>
      ) : (
        <DataTable
          columns={articleColumns}
          data={rows}
          manualPagination
          pageCount={pageCount}
          rowCount={total}
          pagination={pagination}
          onPaginationChange={setPagination}
        />
      )}
    </PageContainer>
  )
}
