import { Link } from '@tanstack/react-router'
import {
  ArrowRightIcon,
  FlaskConicalIcon,
  type LucideIcon,
  SparklesIcon,
  WrenchIcon,
} from 'lucide-react'
import {
  type CSSProperties,
  type ReactNode,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'

import AuthModal from '@/components/Auth/AuthModal'
import type { AuthMode } from '@/components/Auth/authTypes'
import { SupportFooterLinks } from '@/components/Legal/SupportFooterLinks'
import { trackGuestEvent } from '@/lib/analytics'

/**
 * Logged-out home experience. A compact, editorial hero introduces the
 * product in a single column, then hands off to the live article feed so
 * guests can read real signals immediately. The right rail stays quiet:
 * one "Tracking" panel that hints at coverage without competing with
 * the feed.
 */
export function GuestLanding({ children }: { children: ReactNode }) {
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<AuthMode>('sign-up')

  // Every CTA click is tagged with its UI location so the admin funnel
  // can answer "which CTA performs?".
  const openAuth = (mode: AuthMode, location: string) => {
    trackGuestEvent(
      mode === 'sign-up' ? 'guest_signup_click' : 'guest_login_click',
      { payload: { metadata: { location } } },
    )
    setAuthMode(mode)
    setAuthOpen(true)
  }

  const scrollToFeed = () => {
    const target = document.getElementById('latest-signals')
    if (!target) {
      return
    }
    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches
    target.scrollIntoView({
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
    })
  }

  return (
    <>
      <div className="pb-12 pt-5 sm:pb-16 sm:pt-9">
        <section
          aria-labelledby="guest-intro-title"
          className="border-b border-slate-200/70 pb-7 sm:pb-10 dark:border-border/70"
        >
          <div className="max-w-2xl">
            <h1
              id="guest-intro-title"
              className="font-display text-[2rem] font-semibold leading-[1.08] tracking-tight text-slate-950 sm:text-[2.75rem] sm:leading-[1.04] dark:text-foreground"
            >
              Stay ahead of AI without the noise.
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-600 sm:mt-5 sm:text-[1.0625rem] sm:leading-[1.65] dark:text-muted-foreground">
              Curated updates from AI labs, research papers, engineering blogs,
              and trusted builders — organized for people working with AI.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-2 sm:mt-7">
              <button
                type="button"
                onClick={() => openAuth('sign-up', 'hero')}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-slate-950 px-5 text-sm font-semibold text-white shadow-[0_8px_20px_-10px_rgba(15,23,42,0.5)] transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:shadow-[0_8px_20px_-10px_rgba(0,0,0,0.6)] dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
              >
                Create free account
                <ArrowRightIcon
                  className="h-4 w-4 stroke-[1.8]"
                  aria-hidden="true"
                />
              </button>
              <button
                type="button"
                onClick={scrollToFeed}
                className="inline-flex h-11 items-center justify-center rounded-full px-4 text-sm font-semibold text-slate-700 transition-colors hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-foreground/80 dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
              >
                Browse latest
              </button>
            </div>

            <p className="mt-5 text-xs text-slate-500 dark:text-muted-foreground">
              Free to read.{' '}
              <button
                type="button"
                onClick={() => openAuth('sign-in', 'hero')}
                className="font-medium text-slate-700 underline-offset-4 hover:underline focus-visible:outline-none focus-visible:underline dark:text-foreground/85"
              >
                Sign in
              </button>{' '}
              to tune your feed.
            </p>
          </div>
        </section>

        <div className="grid gap-8 pt-6 sm:pt-9 lg:grid-cols-[minmax(0,1fr)_300px] lg:gap-10 xl:gap-12">
          <main className="min-w-0">
            <section
              id="latest-signals"
              aria-labelledby="latest-signals-title"
              className="scroll-mt-24"
            >
              <div className="mb-2 flex items-baseline justify-between gap-3 sm:mb-3">
                <h2
                  id="latest-signals-title"
                  className="font-display text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl dark:text-foreground"
                >
                  Latest signals
                </h2>
              </div>
              {children}
            </section>
          </main>

          <GuestTrackingPanel />
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

interface TrackingRow {
  title: string
  description: string
  Icon: LucideIcon
  cat: 'models' | 'research' | 'engineering'
}

const TRACKING_ROWS: TrackingRow[] = [
  {
    title: 'AI Labs',
    description: 'Model releases, safety updates, and product announcements',
    Icon: SparklesIcon,
    cat: 'models',
  },
  {
    title: 'Research',
    description: 'Papers, benchmarks, and evaluation methods',
    Icon: FlaskConicalIcon,
    cat: 'research',
  },
  {
    title: 'Engineering',
    description: 'RAG, agents, tooling, and production patterns',
    Icon: WrenchIcon,
    cat: 'engineering',
  },
]

function GuestTrackingPanel() {
  const sidebarRef = useRef<HTMLElement>(null)
  const [sidebarHeight, setSidebarHeight] = useState(0)

  // Mirrors the authed Sidebar: if the rail is taller than the viewport,
  // let it scroll with the page until its bottom edge reaches the
  // viewport bottom, then re-stick.
  useLayoutEffect(() => {
    const sidebar = sidebarRef.current
    if (!sidebar) {
      return
    }

    const updateHeight = () => {
      setSidebarHeight(Math.ceil(sidebar.getBoundingClientRect().height))
    }
    updateHeight()

    if (typeof ResizeObserver === 'undefined') {
      return
    }
    const observer = new ResizeObserver(updateHeight)
    observer.observe(sidebar)
    return () => observer.disconnect()
  }, [])

  const sidebarStyle: CSSProperties = {
    top:
      sidebarHeight > 0
        ? `min(6.5rem, calc(100vh - ${sidebarHeight}px - 2rem))`
        : '6.5rem',
  }

  return (
    <aside
      ref={sidebarRef}
      style={sidebarStyle}
      aria-labelledby="guest-tracking-title"
      className="hidden self-start lg:sticky lg:block lg:border-l lg:border-slate-200/70 lg:pl-8 dark:lg:border-border/70"
    >
      <p
        id="guest-tracking-title"
        className="mb-5 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-muted-foreground"
      >
        Tracking
      </p>
      <ul className="space-y-5">
        {TRACKING_ROWS.map(({ title, description, Icon, cat }) => (
          <li key={title}>
            <Link
              to="/category-feed/$cat"
              params={{ cat }}
              onClick={() =>
                trackGuestEvent('guest_topic_click', {
                  payload: { topic: cat },
                })
              }
              className="group block rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition-colors group-hover:bg-slate-950 group-hover:text-white dark:bg-muted/55 dark:text-muted-foreground dark:group-hover:bg-foreground dark:group-hover:text-background">
                  <Icon className="h-3.5 w-3.5 stroke-[1.7]" />
                </span>
                <div className="min-w-0">
                  <p className="text-[0.9375rem] font-medium leading-6 text-slate-950 transition-colors group-hover:text-slate-700 dark:text-foreground dark:group-hover:text-foreground/85">
                    {title}
                  </p>
                  <p className="mt-0.5 text-[0.8125rem] leading-5 text-slate-500 dark:text-muted-foreground">
                    {description}
                  </p>
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>

      <Link
        to="/all-article-sources"
        className="mt-6 inline-flex items-center gap-1 rounded-sm text-xs font-semibold text-slate-500 transition-colors hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-muted-foreground dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
      >
        Browse all sources
        <ArrowRightIcon className="h-3 w-3 stroke-2" aria-hidden="true" />
      </Link>

      <div className="mt-8 border-t border-slate-200/70 pt-5 dark:border-border/70">
        <SupportFooterLinks variant="wrap" withCopyright />
      </div>
    </aside>
  )
}
