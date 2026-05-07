import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export const AUTH_INPUT_CLASS =
  'h-10 rounded-[5px] border border-slate-300 bg-white px-4 text-sm text-slate-950 shadow-none placeholder:text-slate-400 focus-visible:border-slate-400 focus-visible:ring-2 focus-visible:ring-slate-200 sm:h-11 sm:text-base dark:border-border dark:bg-muted/35 dark:text-foreground dark:placeholder:text-muted-foreground dark:focus-visible:border-ring/55 dark:focus-visible:ring-ring/15'

export const AUTH_LABEL_CLASS =
  'text-sm font-semibold leading-none text-slate-700 dark:text-foreground/88'

interface ProviderButtonProps {
  children: ReactNode
  compact?: boolean
  icon: ReactNode
  onClick: () => void
}

export const primaryButtonClass =
  'h-10 w-full rounded-[5px] bg-[#0f172a] text-sm font-semibold text-white shadow-none hover:bg-[#111827] sm:h-11 sm:text-base dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/88'

export function ProviderButton({
  children,
  compact = false,
  icon,
  onClick,
}: ProviderButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        'grid w-full items-center rounded-[5px] border bg-white px-2.5 text-center font-semibold text-slate-950 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300 dark:bg-muted/35 dark:text-foreground/88 dark:hover:bg-accent/80 dark:hover:text-foreground dark:focus-visible:ring-ring/15',
        compact
          ? 'h-10 grid-cols-[32px_1fr_32px] text-sm sm:h-11 sm:grid-cols-[36px_1fr_36px] sm:text-base'
          : 'h-10 grid-cols-[32px_1fr_32px] text-sm sm:h-11 sm:grid-cols-[36px_1fr_36px] sm:text-base',
        'border-slate-200 dark:border-border',
      )}
      onClick={onClick}
    >
      <span className="flex items-center justify-center">{icon}</span>
      <span className="truncate">{children}</span>
      <span aria-hidden="true" />
    </button>
  )
}
