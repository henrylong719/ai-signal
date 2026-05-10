import { ArrowRightIcon, SparklesIcon } from 'lucide-react'
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
import ArticleSource from './ArticleSource'
import RecommendedTopics from './RecommendedTopics'
import TodayDigest from './TodayDigest'

/**
 * Logged-out home experience. The article feed stays central so guests can
 * understand the product by reading it, with a compact intro and secondary rail.
 */
export function GuestLanding({
  children,
}: {
  children: ReactNode
  latestUpdatedAt?: number
}) {
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<AuthMode>('sign-up')

  const openAuth = (mode: AuthMode) => {
    setAuthMode(mode)
    setAuthOpen(true)
  }

  return (
    <>
      <div className="pb-14 pt-7 sm:pb-18 sm:pt-9">
        <section
          aria-labelledby="guest-intro-title"
          className="border-b border-slate-200/80 pb-6 dark:border-border/80"
        >
          <p className="mb-4 inline-flex w-fit items-center gap-2 rounded-full border border-slate-200/70 bg-white/75 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 shadow-[0_1px_1px_rgba(15,23,42,0.025)] dark:border-border dark:bg-muted/35 dark:text-muted-foreground dark:shadow-none">
            <SparklesIcon
              className="h-3.5 w-3.5 stroke-[1.8]"
              aria-hidden="true"
            />
            AI Signal
          </p>

          <div className="max-w-[880px]">
            <div>
              <h1
                id="guest-intro-title"
                className="max-w-[820px] font-display text-4xl font-semibold leading-[1.04] tracking-tight text-slate-950 sm:text-5xl dark:text-foreground"
              >
                Track the AI updates that matter.
              </h1>
              <p className="mt-5 text-base leading-7 text-slate-600 sm:text-lg sm:leading-8 dark:text-muted-foreground">
                A calm reading layer for important AI research, product
                launches, engineering posts, and trusted voices.
              </p>
              <p className="mt-5 flex flex-wrap items-baseline gap-x-2 gap-y-1 text-slate-500 dark:text-foreground/72">
                <span className="font-sans text-xs font-semibold uppercase leading-6 tracking-[0.14em] text-slate-400 dark:text-muted-foreground/70">
                  Curated from
                </span>
                <span className="flex flex-wrap items-baseline gap-x-2 gap-y-1 font-serif text-[0.9375rem] leading-7 sm:text-[1.0625rem]">
                  <span>AI labs</span>
                  <span className="font-sans text-slate-300 dark:text-muted-foreground/35">
                    |
                  </span>
                  <span>Research papers</span>
                  <span className="font-sans text-slate-300 dark:text-muted-foreground/35">
                    |
                  </span>
                  <span>Engineering blogs</span>

                  <span className="font-sans text-slate-300 dark:text-muted-foreground/35">
                    |
                  </span>

                  <span>Newsletters</span>
                  <span className="font-sans text-slate-300 dark:text-muted-foreground/35">
                    |
                  </span>
                  <span>Trusted voices</span>
                </span>
              </p>

              <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                <button
                  type="button"
                  onClick={() => openAuth('sign-up')}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-slate-950 px-5 text-sm font-semibold text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Create free account
                  <ArrowRightIcon
                    className="h-4 w-4 stroke-[1.8]"
                    aria-hidden="true"
                  />
                </button>
                <a
                  href="#latest-signals"
                  className="inline-flex h-10 items-center justify-center rounded-full border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.025)] transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-muted/45 dark:text-foreground/86 dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Browse latest
                </a>
                <button
                  type="button"
                  onClick={() => openAuth('sign-in')}
                  className="inline-flex h-10 items-center justify-center rounded-full px-3 text-sm font-semibold text-slate-500 transition-colors hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-muted-foreground dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Sign in
                </button>
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-8 pt-5 lg:grid-cols-[minmax(0,1fr)_320px] xl:gap-10">
          <MobileGuestBriefing />

          <main className="min-w-0">
            <section
              id="latest-signals"
              aria-labelledby="latest-signals-title"
              className="scroll-mt-24"
            >
              <div className="mb-2 flex flex-col gap-3 sm:mb-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2
                    id="latest-signals-title"
                    className="font-display text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl dark:text-foreground"
                  >
                    Latest signals
                  </h2>
                </div>
              </div>
              {children}
            </section>
          </main>

          <GuestSidebar />
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

function MobileGuestBriefing() {
  return (
    <aside className="rounded-2xl border border-slate-200/70 bg-white/70 p-4 shadow-[0_1px_1px_rgba(15,23,42,0.025)] lg:hidden dark:border-border/70 dark:bg-card/35 dark:shadow-none">
      <TodayDigest />
    </aside>
  )
}

function GuestSidebar() {
  const sidebarRef = useRef<HTMLElement>(null)
  const [sidebarHeight, setSidebarHeight] = useState(0)

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

  // When the rail is taller than the viewport, let it scroll with the page
  // until its bottom edge reaches the viewport.
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
      className="hidden border-t border-slate-200/70 pt-7 lg:sticky lg:block lg:self-start lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0 dark:border-border/70"
    >
      <div className="divide-y divide-slate-200/70 *:py-7 [&>*:first-child]:pt-0 [&>*:last-child]:pb-0 dark:divide-border">
        <TodayDigest />
        <RecommendedTopics />
        <ArticleSource />
      </div>
      <div className="mt-7 border-t border-slate-200/70 pt-5 dark:border-border/70">
        <SupportFooterLinks variant="wrap" withCopyright />
      </div>
    </aside>
  )
}
