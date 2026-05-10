import type { ReactNode } from 'react'
import ScrollAuthPrompt from '@/components/Auth/ScrollAuthPrompt'
import Header from '@/components/Common/Header'
import {
  pageContainerGutters,
  pageContainerWidths,
} from '@/components/Layout/Page'
import { SupportFooterLinks } from '@/components/Legal/SupportFooterLinks'
import { OnboardingDialog } from '@/components/Onboarding/OnboardingDialog'
import { cn } from '@/lib/utils'

interface AppShellProps {
  children: ReactNode
}

export const MAIN_CONTENT_ID = 'main-content'

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Keyboard-only skip link — visually hidden until focused, lets
          tab-only users jump past the header straight to the page body. */}
      <a
        href={`#${MAIN_CONTENT_ID}`}
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:inline-flex focus:h-10 focus:items-center focus:rounded-full focus:bg-slate-950 focus:px-4 focus:text-sm focus:font-medium focus:text-white focus:shadow-md focus:outline-none focus:ring-2 focus:ring-slate-950/15 focus:ring-offset-2 dark:focus:bg-foreground dark:focus:text-background dark:focus:ring-ring/35 dark:focus:ring-offset-background"
      >
        Skip to main content
      </a>
      <Header />
      <main id={MAIN_CONTENT_ID} className={cn('flex-1', pageContainerGutters)}>
        <div className={cn('mx-auto w-full', pageContainerWidths.default)}>
          {children}
        </div>
      </main>
      <footer
        className={cn(
          'border-t border-slate-200/70 bg-background dark:border-border/70',
          pageContainerGutters,
        )}
      >
        <div
          className={cn(
            'mx-auto w-full py-6 sm:py-7',
            pageContainerWidths.default,
          )}
        >
          <SupportFooterLinks variant="inline" withCopyright />
        </div>
      </footer>
      <ScrollAuthPrompt />
      <OnboardingDialog />
    </div>
  )
}
