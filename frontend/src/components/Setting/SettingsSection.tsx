import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

function SettingsSection({
  title,
  description,
  icon,
  danger = false,
  children,
  className,
}: {
  title: string
  description: string
  icon: ReactNode
  danger?: boolean
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={cn(
        'overflow-hidden rounded-lg border bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_32px_rgba(15,23,42,0.04)] dark:bg-card/35 dark:shadow-none',
        danger
          ? 'border-red-200/80 dark:border-red-400/20'
          : 'border-slate-200/80 dark:border-border',
        className,
      )}
    >
      <div
        className={cn(
          'flex gap-4 border-b px-5 py-4 sm:px-6',
          danger
            ? 'border-red-100 bg-red-50/60 dark:border-red-400/15 dark:bg-transparent'
            : 'border-slate-100 bg-slate-50/70 dark:border-border dark:bg-transparent',
        )}
      >
        <div
          className={cn(
            'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border',
            danger
              ? 'border-red-200 bg-white text-red-600 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-300'
              : 'border-slate-200 bg-white text-slate-600 dark:border-border dark:bg-muted/35 dark:text-muted-foreground',
          )}
        >
          {icon}
        </div>
        <div className="min-w-0">
          <h2
            className={cn(
              'text-base font-semibold tracking-tight',
              danger
                ? 'text-red-950 dark:text-red-100'
                : 'text-slate-950 dark:text-foreground',
            )}
          >
            {title}
          </h2>
          <p
            className={cn(
              'mt-1 text-sm leading-6',
              danger
                ? 'text-red-700/75 dark:text-red-200/70'
                : 'text-slate-500 dark:text-muted-foreground',
            )}
          >
            {description}
          </p>
        </div>
      </div>
      <div className="p-5 sm:p-6">{children}</div>
    </section>
  )
}

export default SettingsSection
