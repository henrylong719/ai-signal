import { useLocation } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import ScrollAuthPrompt from '@/components/Auth/ScrollAuthPrompt'
import Header from '@/components/Common/Header'
import {
  pageContainerGutters,
  pageContainerWidths,
} from '@/components/Layout/Page'
import { SupportFooterLinks } from '@/components/Legal/SupportFooterLinks'
import { cn } from '@/lib/utils'

interface AppShellProps {
  children: ReactNode
}

// Routes that already surface the support links in the desktop right
// rail. On those routes we hide the global footer at lg+ to avoid two
// visible copies of the same links; mobile/tablet still see the footer
// because the rail is hidden below lg.
const DESKTOP_RAIL_ROUTES = new Set<string>(['/'])

export function AppShell({ children }: AppShellProps) {
  const { pathname } = useLocation()
  const hideFooterOnDesktop = DESKTOP_RAIL_ROUTES.has(pathname)

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Header />
      <main className={cn('flex-1', pageContainerGutters)}>
        <div className={cn('mx-auto w-full', pageContainerWidths.shell)}>
          {children}
        </div>
      </main>
      <footer
        className={cn(
          'border-t border-slate-200/70 bg-background dark:border-border/70',
          pageContainerGutters,
          hideFooterOnDesktop && 'lg:hidden',
        )}
      >
        <div
          className={cn(
            'mx-auto w-full py-6 sm:py-7',
            pageContainerWidths.shell,
          )}
        >
          <SupportFooterLinks variant="inline" withCopyright />
        </div>
      </footer>
      <ScrollAuthPrompt />
    </div>
  )
}
