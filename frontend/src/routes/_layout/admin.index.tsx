import { useSuspenseQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { Activity, Newspaper } from 'lucide-react'
import { Suspense } from 'react'

import { type UserPublic, UsersService } from '@/client'
import AddUser from '@/components/Admin/AddUser'
import { columns, type UserTableData } from '@/components/Admin/columns'
import { DataTable } from '@/components/Common/DataTable'
import { PageContainer, PageHeader } from '@/components/Layout/Page'
import PendingUsers from '@/components/Pending/PendingUsers'
import { Button } from '@/components/ui/button'
import useAuth from '@/hooks/useAuth'

function getUsersQueryOptions() {
  return {
    queryFn: () => UsersService.readUsers({ skip: 0, limit: 100 }),
    queryKey: ['users'],
  }
}

export const Route = createFileRoute('/_layout/admin/')({
  component: AdminIndex,
  head: () => ({
    meta: [
      {
        title: 'Admin - AI Signal',
      },
    ],
  }),
})

function UsersTableContent() {
  const { user: currentUser } = useAuth()
  const { data: users } = useSuspenseQuery(getUsersQueryOptions())

  const tableData: UserTableData[] = users.data.map((user: UserPublic) => ({
    ...user,
    isCurrentUser: currentUser?.id === user.id,
  }))

  return <DataTable columns={columns} data={tableData} />
}

function UsersTable() {
  return (
    <Suspense fallback={<PendingUsers />}>
      <UsersTableContent />
    </Suspense>
  )
}

function AdminIndex() {
  return (
    <PageContainer
      // variant="narrow"
      spacing="compact"
      className="flex flex-col gap-6"
    >
      <PageHeader
        className="mb-0 border-slate-200/70 pb-6"
        eyebrow="Admin"
        eyebrowClassName="tracking-[0.18em] text-slate-400"
        title="Users"
        titleClassName="tracking-normal"
        description="Manage user accounts and permissions."
        descriptionClassName="max-w-xl"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" asChild className="gap-2">
              <Link to="/admin/articles">
                <Newspaper className="size-3.5" />
                Articles
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild className="gap-2">
              <Link to="/admin/ingest-runs">
                <Activity className="size-3.5" />
                Ingest Runs
              </Link>
            </Button>
            <AddUser />
          </div>
        }
      />
      <UsersTable />
    </PageContainer>
  )
}
