import { createFileRoute, Link } from '@tanstack/react-router'
import { LibraryIcon, SlidersHorizontalIcon } from 'lucide-react'
import { DateTime } from 'luxon'
import { useMemo, useRef, useState } from 'react'
import { z } from 'zod'
import { ArticleList } from '@/components/Articles/ArticleList'
import type { RecommenderDebugPayload } from '@/components/Articles/RecommenderDebugPanel'
import { MobileSidebar, Sidebar } from '@/components/Landing/Sidebar'
import { PageContainer } from '@/components/Layout/Page'
import { GuestPersonalizationCard } from '@/components/Personalization/GuestPersonalizationCard'
import { PersonalizationCard } from '@/components/Personalization/PersonalizationCard'
import { useArticleFeed } from '@/hooks/useArticleFeed'
import useAuth from '@/hooks/useAuth'
import { useFollowingFeed } from '@/hooks/useFollowingFeed'
import { useForYouFeed } from '@/hooks/useForYouFeed'
import { useInterests } from '@/hooks/useInterests'

// `?debug=1` opts a superuser into the recommender-debug panel. Accepts
// the conventional truthy strings (`1`, `true`) and the bare presence
// (`?debug`). Anything else (including absent) coerces to false.
// .catch(false) means a malformed value silently degrades rather than
// erroring the route — debug is a tooling concern, not a load-bearing
// route param.
const searchSchema = z.object({
  debug: z
    .union([z.boolean(), z.string()])
    .optional()
    .transform((v) => v === true || v === '1' || v === 'true' || v === '')
    .catch(false),
})

export const Route = createFileRoute('/_layout/')({
  component: Dashboard,
  validateSearch: searchSchema,
  head: () => ({
    meta: [
      {
        title: 'AI Signal',
      },
    ],
  }),
})

type Tab = 'for-you' | 'following' | 'latest'

interface TabDef {
  value: Tab
  label: string
  authOnly?: boolean
}

const ALL_TABS: TabDef[] = [
  { value: 'for-you', label: 'For you', authOnly: true },
  { value: 'following', label: 'Following', authOnly: true },
  { value: 'latest', label: 'Latest' },
]

function Dashboard() {
  const { debug: debugParam } = Route.useSearch()
  const { user } = useAuth()
  const isAuthed = !!user
  const visibleTabs = useMemo(
    () => ALL_TABS.filter((tab) => !tab.authOnly || isAuthed),
    [isAuthed],
  )
  const [activeTab, setActiveTab] = useState<Tab>(() =>
    isAuthed ? 'for-you' : 'latest',
  )
  // Guests should never see auth-only tabs — if a previously-authed
  // session left activeTab on 'for-you' or 'following' (e.g. after
  // logout in another tab), normalize back to 'latest' instead of
  // rendering an auth-only feed.
  const isAuthOnly = (tab: Tab): boolean =>
    tab === 'for-you' || tab === 'following'
  const resolvedTab: Tab =
    !isAuthed && isAuthOnly(activeTab) ? 'latest' : activeTab
  const feedTopRef = useRef<HTMLDivElement>(null)
  const latestQuery = useArticleFeed()
  const { dataUpdatedAt: latestFeedUpdatedAt, ...latest } = latestQuery
  const following = useFollowingFeed()

  // Debug mode is the AND of "URL asked for it" and "user is privileged".
  // The backend silently ignores ?debug=1 from non-superusers, but
  // gating client-side too means the debug query key matches what the
  // server actually returned, avoiding a wasted refetch when a regular
  // user lands on a debug URL pasted from a superuser session.
  const debugRequested = !!debugParam && !!user?.is_superuser

  // useForYouFeed always runs, but its query needs auth — when the user
  // isn't logged in we render the sign-in CTA instead. Calling the hook
  // unconditionally keeps the hooks order stable.
  const forYou = useForYouFeed({ debug: debugRequested })
  // The activation card needs to know how many preferences the user has set.
  // useInterests is auth-gated so this is a no-op for anonymous visitors.
  const { interests } = useInterests()

  // Threshold: show the card while the user has fewer than 3 total signals
  // across topics, tags, and preferred sources. At 3+ they've meaningfully
  // engaged and the recommender has enough to differentiate articles.
  const totalPreferences =
    (interests?.categories?.length ?? 0) +
    (interests?.tags?.length ?? 0) +
    (interests?.preferred_sources?.length ?? 0)
  const showActivationCard = !!user && totalPreferences < 3

  // Build a stable id→reason map. ForYouArticle extends ArticlePublic so
  // the underlying article objects are compatible with ArticleList; the
  // reason is passed alongside via this map.
  const forYouReasons = useMemo(() => {
    const m = new Map<string, string | null>()
    for (const article of forYou.articles) {
      m.set(article.id, article.reason ?? null)
    }
    return m
  }, [forYou.articles])

  // Parallel id→debug map. Only populated when the backend actually
  // returned debug payloads (i.e. effective debug = requested AND
  // superuser at the server). When empty the map is still passed
  // through but lookups all miss and no panels render.
  const forYouDebug = useMemo(() => {
    const m = new Map<string, RecommenderDebugPayload>()
    if (!debugRequested) {
      return m
    }
    for (const article of forYou.articles) {
      // The generated client may not yet expose `debug` on the type
      // before the next OpenAPI codegen run — narrow defensively so
      // this compiles either way.
      const dbg = (article as { debug?: RecommenderDebugPayload | null }).debug
      if (dbg) {
        m.set(article.id, dbg)
      }
    }
    return m
  }, [forYou.articles, debugRequested])

  const handleTabChange = (tab: Tab) => {
    if (tab === resolvedTab) {
      return
    }

    setActiveTab(tab)
    window.requestAnimationFrame(() => {
      feedTopRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    })
  }

  return (
    <PageContainer
      variant="wide"
      spacing="none"
      className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px] xl:gap-10"
    >
      <div className="min-w-0">
        <div
          ref={feedTopRef}
          className="scroll-mt-16 sm:scroll-mt-18"
          aria-hidden="true"
        />

        <div
          id="homepage-feed"
          className="sticky top-16 z-40 -mx-4 border-b border-slate-200/80 bg-white/95 px-4 pt-3 backdrop-blur sm:top-[72px] sm:-mx-6 sm:px-6 lg:mx-0 lg:px-0 dark:border-border/80 dark:bg-background/92"
        >
          <div className="flex items-center">
            <MobileSidebar />
            <div className="flex gap-8 sm:gap-10">
              {visibleTabs.map((tab) => (
                <button
                  key={tab.value}
                  type="button"
                  onClick={() => handleTabChange(tab.value)}
                  className={`relative rounded-sm pb-5 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-4 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background ${
                    resolvedTab === tab.value
                      ? 'text-slate-950 dark:text-foreground'
                      : 'text-slate-500 hover:text-slate-800 dark:text-muted-foreground dark:hover:text-foreground/86'
                  }`}
                >
                  {tab.label}
                  {resolvedTab === tab.value && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-slate-950 dark:bg-primary" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {!isAuthed &&
          resolvedTab === 'latest' &&
          !latest.isPending &&
          !latest.isError &&
          latestFeedUpdatedAt > 0 && (
            <p className="mt-3 text-xs font-medium text-slate-500 dark:text-muted-foreground/85">
              Feed updated{' '}
              {DateTime.fromMillis(latestFeedUpdatedAt).toRelative()}
            </p>
          )}

        {resolvedTab === 'for-you' && isAuthed && (
          <>
            {showActivationCard && <PersonalizationCard />}
            {debugRequested && forYou.weights && (
              <div className="mt-4 rounded border border-dashed border-amber-300/60 bg-amber-50/40 px-3 py-2 font-mono text-[11px] text-amber-900 dark:border-amber-500/30 dark:bg-amber-950/15 dark:text-amber-200/85">
                <span className="font-sans font-semibold uppercase tracking-wide">
                  recommender weights
                </span>{' '}
                <span className="opacity-80">
                  semantic={forYou.weights.semantic.toFixed(2)} explicit=
                  {forYou.weights.explicit.toFixed(2)} source=
                  {forYou.weights.source.toFixed(2)} recency=
                  {forYou.weights.recency.toFixed(2)}
                </span>
              </div>
            )}
            <ArticleList
              articles={forYou.articles}
              feedStatus={forYou.feedStatus}
              loadMoreRef={forYou.loadMoreRef}
              isPending={forYou.isPending}
              isError={forYou.isError}
              showDismiss
              reasons={forYouReasons}
              debug={forYouDebug}
              emptyTitle="No personalized signals yet"
              emptyDescription="Save articles you care about or tune topics and sources — your For You feed learns from what you engage with."
              emptyAction={
                <Link
                  to="/personalization"
                  className="inline-flex h-9 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  <SlidersHorizontalIcon className="h-4 w-4 stroke-[1.7]" />
                  Tune your signal
                </Link>
              }
            />
          </>
        )}
        {resolvedTab === 'following' && isAuthed && (
          <ArticleList
            {...following}
            emptyTitle={
              (interests?.preferred_sources?.length ?? 0) === 0
                ? 'Follow sources to build your trusted AI reading list'
                : 'No new articles from your followed sources yet'
            }
            emptyDescription={
              (interests?.preferred_sources?.length ?? 0) === 0
                ? 'Choose the labs, newsletters, research feeds, and communities you care about most.'
                : 'New posts from your followed sources will appear here when they are ingested.'
            }
            emptyAction={
              (interests?.preferred_sources?.length ?? 0) === 0 ? (
                <Link
                  to="/all-article-sources"
                  className="inline-flex h-9 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  <LibraryIcon className="h-4 w-4 stroke-[1.7]" />
                  Browse sources
                </Link>
              ) : (
                <button
                  type="button"
                  onClick={() => handleTabChange('latest')}
                  className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-muted/45 dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Explore latest articles
                </button>
              )
            }
          />
        )}
        {resolvedTab === 'latest' && (
          <>
            {!isAuthed && <GuestPersonalizationCard />}
            <ArticleList
              {...latest}
              emptyTitle="Nothing in Latest yet"
              emptyDescription="Fresh signals will land here as we ingest new posts from labs, research, engineering blogs, and newsletters."
            />
          </>
        )}
      </div>
      <Sidebar />
    </PageContainer>
  )
}
