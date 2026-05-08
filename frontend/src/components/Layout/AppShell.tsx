import type { ReactNode } from 'react'
import ScrollAuthPrompt from '@/components/Auth/ScrollAuthPrompt'
import Header from '@/components/Common/Header'
import {
  pageContainerGutters,
  pageContainerWidths,
} from '@/components/Layout/Page'
import { cn } from '@/lib/utils'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <main className={pageContainerGutters}>
        <div className={cn('mx-auto w-full', pageContainerWidths.shell)}>
          {children}
        </div>
      </main>
      <ScrollAuthPrompt />
    </div>
  )
}
