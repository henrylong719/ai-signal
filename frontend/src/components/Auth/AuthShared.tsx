import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export const AUTH_INPUT_CLASS =
  'h-10 rounded-[5px] border border-slate-300 bg-white px-3.5 text-sm text-slate-950 shadow-none placeholder:text-slate-400 focus-visible:border-slate-400 focus-visible:ring-2 focus-visible:ring-slate-200 dark:border-border dark:bg-muted/35 dark:text-foreground dark:placeholder:text-muted-foreground dark:focus-visible:border-ring/55 dark:focus-visible:ring-ring/15'

export const AUTH_LABEL_CLASS =
  'text-xs font-semibold leading-none text-slate-600 dark:text-foreground/78'

interface ProviderButtonProps {
  children: ReactNode
  emphasis?: 'primary' | 'secondary'
  icon: ReactNode
  onClick: () => void
}

export const primaryButtonClass =
  'h-10 w-full rounded-full border border-slate-950 bg-slate-950 text-sm font-semibold text-white shadow-sm shadow-slate-950/10 hover:bg-slate-800 dark:border-foreground dark:bg-foreground dark:text-background dark:hover:bg-foreground/92'

export function ProviderButton({
  children,
  emphasis = 'secondary',
  icon,
  onClick,
}: ProviderButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        'grid h-11 w-full grid-cols-[36px_1fr_36px] items-center rounded-[6px] border px-2.5 text-center text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300 dark:focus-visible:ring-ring/15',
        emphasis === 'primary'
          ? 'border-slate-300 bg-white text-slate-950 shadow-[0_1px_2px_rgba(15,23,42,0.05)] hover:border-slate-400 hover:bg-slate-50 dark:border-foreground/18 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92'
          : 'border-slate-200 bg-white text-slate-800 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 dark:border-border dark:bg-muted/35 dark:text-foreground/88 dark:hover:bg-accent/80 dark:hover:text-foreground',
      )}
      onClick={onClick}
    >
      <span className="flex items-center justify-center">{icon}</span>
      <span className="truncate">{children}</span>
      <span aria-hidden="true" />
    </button>
  )
}
