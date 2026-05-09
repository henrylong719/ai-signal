import { Link } from '@tanstack/react-router'
import { Fragment } from 'react'
import { SUPPORT_LINKS } from '@/lib/legal'
import { cn } from '@/lib/utils'

interface SupportFooterLinksProps {
  className?: string
  // Whether to render a copyright line under the link group. Off by
  // default so the component can drop into tight spaces (rail/sheet) and
  // opt in only on broader landing/auth surfaces.
  withCopyright?: boolean
  // 'inline' draws bullet separators between links (X-style); 'wrap'
  // omits them so links flow as standalone chips on narrow screens.
  variant?: 'inline' | 'wrap'
}

export function SupportFooterLinks({
  className,
  withCopyright = false,
  variant = 'inline',
}: SupportFooterLinksProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-2 text-xs text-slate-500 dark:text-muted-foreground',
        className,
      )}
    >
      <nav aria-label="Support and legal" className="-mx-1">
        <ul
          className={cn(
            'flex flex-wrap items-center',
            variant === 'inline' ? 'gap-x-1 gap-y-1.5' : 'gap-x-3 gap-y-1.5',
          )}
        >
          {SUPPORT_LINKS.map((link, index) => (
            <Fragment key={link.to}>
              <li>
                <Link
                  to={link.to}
                  className="inline-flex rounded-full px-2 py-1.5 transition-colors hover:text-slate-900 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  {link.label}
                </Link>
              </li>
              {variant === 'inline' && index < SUPPORT_LINKS.length - 1 && (
                <li
                  aria-hidden="true"
                  className="select-none text-slate-300 dark:text-muted-foreground/55"
                >
                  ·
                </li>
              )}
            </Fragment>
          ))}
        </ul>
      </nav>
      {withCopyright && (
        <p className="px-1 text-slate-400 dark:text-muted-foreground/75">
          © {new Date().getFullYear()} AI Signal
        </p>
      )}
    </div>
  )
}
