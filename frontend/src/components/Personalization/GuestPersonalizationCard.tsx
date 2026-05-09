import { SparklesIcon } from 'lucide-react'
import { useState } from 'react'

import AuthModal from '@/components/Auth/AuthModal'
import type { AuthMode } from '@/components/Auth/authTypes'

/**
 * Soft inline activation prompt shown to guests on the Latest feed.
 *
 * Replaces the previous blocking auth popup that triggered when a guest
 * tapped the For-You tab. Buttons open the same AuthModal the header
 * already uses, just with a controlled initialMode so "Create account"
 * lands the user on the sign-up email screen and "Sign in" on the
 * sign-in screen after they pick the email provider.
 */
export function GuestPersonalizationCard() {
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<AuthMode>('sign-in')

  const openAuth = (mode: AuthMode) => {
    setAuthMode(mode)
    setAuthOpen(true)
  }

  return (
    <>
      <div className="mb-6 mt-6 rounded-lg border border-slate-200/80 bg-white p-5 dark:border-border dark:bg-card/35 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-slate-50 text-slate-600 dark:border-border dark:bg-muted/35 dark:text-muted-foreground">
              <SparklesIcon className="h-4 w-4 stroke-[1.7]" />
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-slate-950 dark:text-foreground">
                Personalize your feed
              </h3>
              <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
                Sign in to save articles, follow trusted sources, and tune your
                feed.
              </p>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2 sm:self-start">
            <button
              type="button"
              onClick={() => openAuth('sign-up')}
              className="inline-flex h-9 items-center rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
            >
              Create account
            </button>
            <button
              type="button"
              onClick={() => openAuth('sign-in')}
              className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-muted/45 dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
            >
              Sign in
            </button>
          </div>
        </div>
      </div>
      <AuthModal
        open={authOpen}
        onOpenChange={setAuthOpen}
        initialMode={authMode}
        trigger={null}
      />
    </>
  )
}
