import { ArrowRightIcon, CalendarIcon, SparklesIcon } from 'lucide-react';
import {
  type CSSProperties,
  type ReactNode,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';

import AuthModal from '@/components/Auth/AuthModal';
import type { AuthMode } from '@/components/Auth/authTypes';
import { SupportFooterLinks } from '@/components/Legal/SupportFooterLinks';
import { useSources } from '@/hooks/useSources';
import { useTodayDigest } from '@/hooks/useTodayDigest';
import { trackGuestEvent } from '@/lib/analytics';
import ArticleSource from './ArticleSource';
import RecommendedTopics from './RecommendedTopics';
import TodayDigest from './TodayDigest';

/**
 * Logged-out home experience. The article feed stays central so guests can
 * understand the product by reading it, with a compact intro and secondary rail.
 */
export function GuestLanding({
  children,
}: {
  children: ReactNode;
  latestUpdatedAt?: number;
}) {
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>('sign-up');

  // The hero hosts both auth CTAs. We tag every CTA click with its UI
  // location so the admin funnel can answer "which CTA performs?".
  const openAuth = (mode: AuthMode, location: string) => {
    trackGuestEvent(
      mode === 'sign-up' ? 'guest_signup_click' : 'guest_login_click',
      { payload: { metadata: { location } } },
    );
    setAuthMode(mode);
    setAuthOpen(true);
  };

  return (
    <>
      <div className="pb-14 pt-7 sm:pb-18 sm:pt-9">
        <section
          aria-labelledby="guest-intro-title"
          className="border-b border-slate-200/80 pb-12 sm:pb-16 dark:border-border/80"
        >
          <div className="grid items-center gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(440px,1.05fr)] lg:gap-14 xl:gap-16">
            <div className="min-w-0">
              <p className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-slate-200/70 bg-white/75 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 shadow-[0_1px_1px_rgba(15,23,42,0.025)] dark:border-border dark:bg-muted/35 dark:text-muted-foreground dark:shadow-none">
                <SparklesIcon
                  className="h-3.5 w-3.5 stroke-[1.8]"
                  aria-hidden="true"
                />
                AI Signal
              </p>

              <h1
                id="guest-intro-title"
                className="max-w-[640px] font-display text-[2.5rem] font-semibold leading-[1.05] tracking-tight text-slate-950 sm:text-[3.25rem] sm:leading-[1.03] dark:text-foreground"
              >
                Stay ahead of AI without the noise.
              </h1>
              <p className="mt-6 max-w-[560px] text-base leading-7 text-slate-600 sm:text-lg sm:leading-8 dark:text-muted-foreground">
                AI Signal curates important updates from AI labs, research
                papers, engineering blogs, newsletters, and trusted voices into
                one calm reading feed.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                <button
                  type="button"
                  onClick={() => openAuth('sign-up', 'hero')}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-slate-950 px-6 text-sm font-semibold text-white shadow-[0_8px_20px_-8px_rgba(15,23,42,0.55)] transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:shadow-[0_8px_20px_-10px_rgba(0,0,0,0.65)] dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Create free account
                  <ArrowRightIcon
                    className="h-4 w-4 stroke-[1.8]"
                    aria-hidden="true"
                  />
                </button>
                <a
                  href="#latest-signals"
                  className="inline-flex h-11 items-center justify-center rounded-full border border-slate-200 bg-white px-6 text-sm font-semibold text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.025)] transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-muted/45 dark:text-foreground/86 dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Browse latest
                </a>
                <button
                  type="button"
                  onClick={() => openAuth('sign-in', 'hero')}
                  className="inline-flex h-11 items-center justify-center rounded-full px-3 text-sm font-semibold text-slate-500 transition-colors hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-muted-foreground dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Sign in
                </button>
              </div>
            </div>

            <HeroProductMockup />
          </div>
        </section>

        <div className="grid gap-8 pt-8 sm:pt-10 lg:grid-cols-[minmax(0,1fr)_320px] xl:gap-10">
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
  );
}

const HERO_MOCKUP_CHIPS = [
  { name: 'All', active: true },
  { name: 'Research' },
  { name: 'Models' },
  { name: 'Engineering' },
  { name: 'Safety' },
];

const HERO_MOCKUP_ARTICLES = [
  {
    source: 'Anthropic',
    topic: 'Research',
    title: 'New interpretability findings map attention circuits',
    time: '2h',
    accent: 'bg-amber-400',
  },
  {
    source: 'DeepMind',
    topic: 'Models',
    title: 'Gemini multimodal embeddings hit a new benchmark',
    time: '5h',
    accent: 'bg-sky-400',
  },
  {
    source: 'Vercel',
    topic: 'Engineering',
    title: 'How we run AI Gateway across 18 regions',
    time: '1d',
    accent: 'bg-emerald-400',
  },
];

function HeroProductMockup() {
  return (
    <div aria-hidden="true" className="relative hidden lg:block">
      <div className="pointer-events-none absolute -inset-x-8 -inset-y-10 -z-10 bg-linear-to-tr from-amber-100/45 via-white to-sky-50/50 blur-3xl dark:from-amber-500/5 dark:via-transparent dark:to-sky-500/5" />

      <div className="relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white shadow-[0_30px_80px_-30px_rgba(15,23,42,0.28)] dark:border-border/80 dark:bg-card dark:shadow-[0_30px_80px_-20px_rgba(0,0,0,0.55)]">
        <div className="flex items-center gap-3 border-b border-slate-200/70 bg-slate-50/70 px-5 py-3 dark:border-border/70 dark:bg-muted/30">
          <div className="flex gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-300/80 dark:bg-muted-foreground/30" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-300/80 dark:bg-muted-foreground/30" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-300/80 dark:bg-muted-foreground/30" />
          </div>
          <div className="mx-auto inline-flex items-center gap-1.5 rounded-md border border-slate-200/70 bg-white px-3 py-1 text-[11px] font-medium text-slate-400 dark:border-border/60 dark:bg-card/80 dark:text-muted-foreground">
            <SparklesIcon className="h-3 w-3 stroke-[1.8]" />
            aisignal.now / digest
          </div>
        </div>

        <div className="px-6 pb-7 pt-6">
          <div className="mb-5 flex items-baseline justify-between">
            <h3 className="font-display text-[1.0625rem] font-semibold tracking-tight text-slate-950 dark:text-foreground">
              Latest signals
            </h3>
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400 dark:text-muted-foreground">
              Today
            </span>
          </div>

          <div className="mb-5 flex flex-wrap gap-1.5">
            {HERO_MOCKUP_CHIPS.map((chip) => (
              <span
                key={chip.name}
                className={
                  chip.active
                    ? 'inline-flex items-center rounded-full bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white dark:bg-foreground dark:text-background'
                    : 'inline-flex items-center rounded-full border border-slate-200/80 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-500 dark:border-border dark:bg-muted/40 dark:text-muted-foreground'
                }
              >
                {chip.name}
              </span>
            ))}
          </div>

          <div className="space-y-3">
            {HERO_MOCKUP_ARTICLES.map((article) => (
              <div
                key={article.title}
                className="rounded-xl border border-slate-200/70 bg-white px-3.5 py-3 dark:border-border/70 dark:bg-card/55"
              >
                <div className="mb-1.5 flex items-center gap-2 text-[11px]">
                  <span
                    className={`inline-block h-1.5 w-1.5 rounded-full ${article.accent}`}
                  />
                  <span className="font-semibold text-slate-700 dark:text-foreground/80">
                    {article.source}
                  </span>
                  <span className="text-slate-300 dark:text-muted-foreground/40">
                    ·
                  </span>
                  <span className="text-slate-500 dark:text-muted-foreground">
                    {article.topic}
                  </span>
                  <span className="ml-auto text-slate-400 dark:text-muted-foreground/70">
                    {article.time}
                  </span>
                </div>
                <p className="font-serif text-[0.9375rem] leading-snug text-slate-950 dark:text-foreground">
                  {article.title}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="absolute -bottom-7 -right-5 w-60 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_18px_44px_-12px_rgba(15,23,42,0.18)] dark:border-border/80 dark:bg-card dark:shadow-[0_18px_44px_-12px_rgba(0,0,0,0.55)]">
        <div className="mb-3 flex items-center gap-2.5">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-slate-950 text-white dark:bg-foreground dark:text-background">
            <CalendarIcon className="h-3.5 w-3.5 stroke-[1.8]" />
          </span>
          <div className="leading-tight">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400 dark:text-muted-foreground">
              Today's digest
            </p>
            <p className="text-[12px] font-semibold text-slate-950 dark:text-foreground">
              5 stories worth reading
            </p>
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <span className="mt-1.5 inline-block h-1 w-1 rounded-full bg-slate-400 dark:bg-muted-foreground/60" />
            <p className="text-[12px] leading-snug text-slate-700 dark:text-foreground/85">
              OpenAI publishes long-horizon agent evaluation
            </p>
          </div>
          <div className="flex items-start gap-2">
            <span className="mt-1.5 inline-block h-1 w-1 rounded-full bg-slate-400 dark:bg-muted-foreground/60" />
            <p className="text-[12px] leading-snug text-slate-700 dark:text-foreground/85">
              Mistral releases an open-weight reasoning model
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MobileGuestBriefing() {
  return (
    <aside className="rounded-2xl border border-slate-200/70 bg-white/70 p-4 shadow-[0_1px_1px_rgba(15,23,42,0.025)] lg:hidden dark:border-border/70 dark:bg-card/35 dark:shadow-none">
      <TodayDigest />
    </aside>
  );
}

function GuestSidebar() {
  const { isLoading: sourcesLoading } = useSources();
  const { isLoading: digestLoading } = useTodayDigest();
  const isLoading = sourcesLoading || digestLoading;

  const sidebarRef = useRef<HTMLElement>(null);
  const [sidebarHeight, setSidebarHeight] = useState(0);

  useLayoutEffect(() => {
    const sidebar = sidebarRef.current;

    if (!sidebar) {
      return;
    }

    const updateHeight = () => {
      setSidebarHeight(Math.ceil(sidebar.getBoundingClientRect().height));
    };

    updateHeight();

    if (typeof ResizeObserver === 'undefined') {
      return;
    }

    const observer = new ResizeObserver(updateHeight);
    observer.observe(sidebar);

    return () => observer.disconnect();
  }, []);

  // When the rail is taller than the viewport, let it scroll with the page
  // until its bottom edge reaches the viewport.
  const sidebarStyle: CSSProperties = {
    top:
      sidebarHeight > 0
        ? `min(6.5rem, calc(100vh - ${sidebarHeight}px - 2rem))`
        : '6.5rem',
  };

  return (
    <aside
      ref={sidebarRef}
      style={sidebarStyle}
      className="hidden border-t border-slate-200/70 pt-7 lg:sticky lg:block lg:self-start lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0 dark:border-border/70"
    >
      <div className="divide-y divide-slate-200/70 *:py-7 [&>*:first-child]:pt-0 [&>*:last-child]:pb-0 dark:divide-border">
        <TodayDigest />
        <RecommendedTopics isLoading={isLoading} />
        <ArticleSource />
      </div>
      <div className="mt-7 border-t border-slate-200/70 pt-5 dark:border-border/70">
        <SupportFooterLinks variant="wrap" withCopyright />
      </div>
    </aside>
  );
}
