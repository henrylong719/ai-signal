import { createFileRoute, redirect } from '@tanstack/react-router'

import AuthFlow from '@/components/Auth/AuthFlow'
import { isLoggedIn } from '@/hooks/useAuth'

export const Route = createFileRoute('/login')({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: '/',
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: 'Log In - AI Signal',
      },
    ],
  }),
})

function Login() {
  return (
    <main className="min-h-svh bg-white text-zinc-900 dark:bg-slate-950 dark:text-slate-100">
      <AuthFlow initialMode="sign-in" className="mx-auto min-h-svh max-w-230" />
    </main>
  )
}
