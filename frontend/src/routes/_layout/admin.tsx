import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { UsersService } from '@/client'

export const Route = createFileRoute('/_layout/admin')({
  component: () => <Outlet />,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({
        to: '/',
      })
    }
  },
})
