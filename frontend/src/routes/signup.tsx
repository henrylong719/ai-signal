import { createFileRoute, redirect } from '@tanstack/react-router'

import AuthFlow from '@/components/Auth/AuthFlow'
import { SupportFooterLinks } from '@/components/Legal/SupportFooterLinks'
import { isLoggedIn } from '@/hooks/useAuth'

export const Route = createFileRoute('/signup')({
  component: SignUp,
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
        title: 'Sign Up - AI Signal',
      },
    ],
  }),
})

function SignUp() {
  return (
    <main className="flex min-h-svh flex-col bg-white text-zinc-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="mx-auto w-full max-w-230 flex-1">
        <AuthFlow initialMode="sign-up" className="min-h-[calc(100svh-4rem)]" />
      </div>
      <div className="mx-auto flex w-full max-w-230 justify-center px-6 pb-8">
        <SupportFooterLinks variant="inline" />
      </div>
    </main>
  )
}
