import { createFileRoute, redirect } from '@tanstack/react-router'

import AuthFlow from '@/components/Auth/AuthFlow'
import { SupportFooterLinks } from '@/components/Legal/SupportFooterLinks'
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
    <main className="flex min-h-svh flex-col bg-background text-foreground">
      <div className="mx-auto w-full max-w-230 flex-1">
        <AuthFlow initialMode="sign-in" className="min-h-[calc(100svh-4rem)]" />
      </div>
      <div className="mx-auto flex w-full max-w-230 justify-center px-6 pb-8">
        <SupportFooterLinks variant="inline" />
      </div>
    </main>
  )
}
