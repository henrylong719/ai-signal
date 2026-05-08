import { useQueryClient, useSuspenseQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { Suspense, useState } from 'react'

import { type AdminArticlePublic, AdminService } from '@/client'
import { articleColumns } from '@/components/Admin/articleColumns'
import { DataTable } from '@/components/Common/DataTable'
import { PageContainer, PageHeader } from '@/components/Layout/Page'
import PendingItems from '@/components/Pending/PendingItems'
import { Button } from '@/components/ui/button'
import useCustomToast from '@/hooks/useCustomToast'
import { cn } from '@/lib/utils'

async function readAllAdminArticles() {
  const limit = 500
  let skip = 0
  let count = 0
  const data: AdminArticlePublic[] = []

  do {
    const page = await AdminService.readAdminArticles({ skip, limit })
    data.push(...page.data)
    count = page.count
    skip += page.data.length

    if (page.data.length === 0) {
      break
    }
  } while (data.length < count)

  return { data, count }
}

function getAdminArticlesQueryOptions() {
  return {
    queryFn: readAllAdminArticles,
    queryKey: ['admin-articles'],
  }
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

function ArticlesTableContent() {
  const { data } = useSuspenseQuery(getAdminArticlesQueryOptions())
  return <DataTable columns={articleColumns} data={data.data} />
}

function ArticlesTable() {
  return (
    <Suspense fallback={<PendingItems />}>
      <ArticlesTableContent />
    </Suspense>
  )
}

function AdminArticlesPage() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [isRefreshing, setIsRefreshing] = useState(false)

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

  return (
    <PageContainer
      variant="wide"
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
      <ArticlesTable />
    </PageContainer>
  )
}
