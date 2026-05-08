import { createFileRoute } from '@tanstack/react-router'
import { AlertCircleIcon, CheckIcon, LogInIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { category as Category, UserInterestPublic } from '@/client'
import { ArticleListState } from '@/components/Articles/ArticleList'
import AuthModal from '@/components/Auth/AuthModal'
import { SourcesField } from '@/components/Personalization/SourcesField'
import { TagsField } from '@/components/Personalization/TagsField'
import { TopicsField } from '@/components/Personalization/TopicsField'
import { LoadingButton } from '@/components/ui/loading-button'
import { Skeleton } from '@/components/ui/skeleton'
import useAuth from '@/hooks/useAuth'
import { useInterests } from '@/hooks/useInterests'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_layout/personalization')({
  component: Personalization,
  head: () => ({
    meta: [
      {
        title: 'Tune your signal · AI Signal',
      },
    ],
  }),
})

const sameItems = <T extends string>(current: T[], saved: T[]) =>
  current.length === saved.length &&
  current.every((item) => saved.includes(item))

const formatCount = (
  count: number,
  singular: string,
  plural = `${singular}s`,
) => `${count} ${count === 1 ? singular : plural}`

function Personalization() {
  const { user, isLoading: authLoading, isError: authError } = useAuth()
  const { interests, isLoading, isError, save, isSaving } = useInterests()

  // Working copy of the form. Initialised from the server value, then
  // mutated locally as the user clicks. We compare against the server
  // value to compute the dirty flag.
  const [categories, setCategories] = useState<Category[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [preferredSources, setPreferredSources] = useState<string[]>([])
  const [hasSyncedInterests, setHasSyncedInterests] = useState(false)

  const syncInterests = useCallback((nextInterests: UserInterestPublic) => {
    setCategories(nextInterests.categories ?? [])
    setTags(nextInterests.tags ?? [])
    setPreferredSources(nextInterests.preferred_sources ?? [])
    setHasSyncedInterests(true)
  }, [])

  const isDirty = useMemo(() => {
    if (!interests) {
      return (
        categories.length > 0 || tags.length > 0 || preferredSources.length > 0
      )
    }
    const savedCategories = interests.categories ?? []
    const savedTags = interests.tags ?? []
    const savedSources = interests.preferred_sources ?? []
    const sameCategories = sameItems(categories, savedCategories)
    const sameTags = sameItems(tags, savedTags)
    const sameSources = sameItems(preferredSources, savedSources)
    return !(sameCategories && sameTags && sameSources)
  }, [categories, tags, preferredSources, interests])

  // Sync initial server values and clean refetches. Dirty local edits are left
  // alone so a background query refresh cannot overwrite in-progress choices.
  useEffect(() => {
    if (!interests) {
      return
    }
    if (hasSyncedInterests && isDirty) {
      return
    }
    syncInterests(interests)
  }, [hasSyncedInterests, interests, isDirty, syncInterests])

  // The introductory note only shifts into onboarding mode when all three
  // lists are empty. Once the user starts, summarize their current signals.
  const showOnboarding =
    !isLoading &&
    !isError &&
    categories.length === 0 &&
    tags.length === 0 &&
    preferredSources.length === 0

  const selectionSummary = useMemo(() => {
    const parts = []
    if (categories.length > 0) {
      parts.push(formatCount(categories.length, 'topic'))
    }
    if (preferredSources.length > 0) {
      parts.push(formatCount(preferredSources.length, 'source'))
    }
    if (tags.length > 0) {
      parts.push(formatCount(tags.length, 'tag'))
    }

    if (parts.length === 0) {
      return 'Start with a few topics. Sources and tags can stay light until you know what you want more of.'
    }

    return `Your profile currently has ${parts.join(', ')}.`
  }, [categories.length, preferredSources.length, tags.length])

  const handleSave = () => {
    save(
      { categories, tags, preferred_sources: preferredSources },
      { onSuccess: syncInterests },
    )
  }

  if (authLoading) {
    return <PersonalizationSkeleton />
  }

  if (authError) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pt-10">
        <ArticleListState
          title="Could not load personalization"
          description="Please refresh the page or try again in a moment."
          icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
        />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pt-10">
        <ArticleListState
          title="Sign in to tune your signal"
          description="Personalization is built from your saved articles and the topics you follow. Sign in to start."
          icon={<LogInIcon className="h-5 w-5 stroke-[1.5]" />}
          action={
            <AuthModal
              trigger={
                <button
                  type="button"
                  className="inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/88 dark:focus-visible:ring-ring dark:focus-visible:ring-offset-background"
                >
                  Sign in
                </button>
              }
            />
          }
        />
      </div>
    )
  }

  if (isLoading) {
    return <PersonalizationSkeleton />
  }

  if (isError) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 pt-10">
        <ArticleListState
          title="Could not load your preferences"
          description="Please refresh the page or try again in a moment."
          icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
        />
      </div>
    )
  }

  const showStickySave = isDirty || isSaving

  return (
    <div
      className={cn(
        'mx-auto w-full max-w-3xl pt-8 sm:pt-12',
        showStickySave ? 'pb-36 sm:pb-40' : 'pb-16 sm:pb-20',
      )}
    >
      <header className="border-b border-slate-200/70 pb-8 dark:border-border">
        <p className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-muted-foreground">
          Taste profile
        </p>
        <h1 className="max-w-2xl font-display text-4xl font-semibold tracking-normal text-slate-950 sm:text-5xl dark:text-foreground">
          Teach AI Signal what matters
        </h1>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600 dark:text-muted-foreground">
          Start with the subjects you never want to miss. Add trusted sources
          and personal tags only when they sharpen the feed.
        </p>

        <div className="mt-6 border-l border-slate-300 pl-4 dark:border-border">
          <p className="text-sm leading-6 text-slate-500 dark:text-muted-foreground">
            {showOnboarding
              ? 'Pick 3 to 5 topics first. The rest can wait.'
              : selectionSummary}
          </p>
        </div>
      </header>

      <div className="divide-y divide-slate-200/70 dark:divide-border">
        <TasteSection
          eyebrow="Start here"
          title="Topics to follow"
          description="These are the broad signals AI Signal should listen for first."
          count={formatCount(categories.length, 'topic')}
        >
          <TopicsField value={categories} onChange={setCategories} />
        </TasteSection>

        <TasteSection
          eyebrow="Optional"
          title="Trusted sources"
          description="Give extra weight to publications, labs, and independent voices you already rely on."
          count={formatCount(preferredSources.length, 'source')}
        >
          <SourcesField
            value={preferredSources}
            onChange={setPreferredSources}
          />
        </TasteSection>

        <TasteSection
          eyebrow="Personal"
          title="Tags and phrases"
          description="Add the names, tools, papers, or ideas that are too specific for a topic."
          count={formatCount(tags.length, 'tag')}
        >
          <TagsField value={tags} onChange={setTags} />
        </TasteSection>
      </div>

      <div className="mt-2 flex flex-col gap-4 border-t border-slate-200/70 pt-6 sm:flex-row sm:items-center sm:justify-between dark:border-border">
        <p className="text-sm leading-6 text-slate-500 dark:text-muted-foreground">
          {isSaving
            ? 'Saving your taste profile...'
            : isDirty
              ? 'Your choices are ready. Save them from the bar below when this feels right.'
              : 'Saved. Your feed is listening for these signals.'}
        </p>
        {!showStickySave && (
          <span className="inline-flex h-10 w-fit items-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-600 shadow-sm shadow-slate-950/[0.02] dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none">
            <CheckIcon className="h-4 w-4" />
            Saved
          </span>
        )}
      </div>

      {showStickySave && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200/80 bg-white/92 px-4 py-3 shadow-[0_-12px_34px_rgba(15,23,42,0.08)] backdrop-blur-md sm:px-6 lg:px-8 dark:border-border dark:bg-background/90 dark:shadow-[0_-12px_34px_rgba(0,0,0,0.22)]">
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-950 dark:text-foreground">
                {isSaving ? 'Saving your taste profile' : 'Unsaved choices'}
              </p>
              <p className="mt-0.5 text-xs leading-5 text-slate-500 dark:text-muted-foreground">
                {isSaving
                  ? 'Your For You feed will update in a moment.'
                  : 'Save these signals so AI Signal can use them in your feed.'}
              </p>
            </div>
            <LoadingButton
              onClick={handleSave}
              loading={isSaving}
              disabled={!isDirty || isSaving}
              size="sm"
              className="h-10 w-full bg-slate-950 px-5 font-medium text-white shadow-sm shadow-slate-950/10 hover:bg-slate-800 sm:w-auto dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/88"
            >
              <CheckIcon className="h-4 w-4" />
              Save taste profile
            </LoadingButton>
          </div>
        </div>
      )}
    </div>
  )
}

function PersonalizationSkeleton() {
  return (
    <div className="mx-auto w-full max-w-3xl pb-16 pt-8 sm:pb-20 sm:pt-12">
      <header className="border-b border-slate-200/70 pb-8 dark:border-border">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-5 h-12 w-full max-w-xl" />
        <Skeleton className="mt-4 h-6 w-full max-w-2xl" />
        <Skeleton className="mt-2 h-6 w-full max-w-lg" />
      </header>
      <div className="divide-y divide-slate-200/70 dark:divide-border">
        {[0, 1, 2].map((i) => (
          <section key={i} className="py-8 sm:py-10">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="mt-3 h-7 w-56" />
            <Skeleton className="mt-2 h-4 w-full max-w-md" />
            <div className="mt-6 flex flex-wrap gap-2.5">
              {[0, 1, 2, 3, 4].map((j) => (
                <Skeleton key={j} className="h-11 w-24 rounded-full" />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}

function TasteSection({
  eyebrow,
  title,
  description,
  count,
  children,
}: {
  eyebrow: string
  title: string
  description: string
  count: string
  children: ReactNode
}) {
  return (
    <section className="py-8 sm:py-10">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-xl">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400 dark:text-muted-foreground">
            {eyebrow}
          </p>
          <h2 className="font-display text-2xl font-semibold tracking-normal text-slate-950 dark:text-foreground">
            {title}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
            {description}
          </p>
        </div>
        <span className="inline-flex min-h-8 w-fit items-center rounded-full border border-slate-200 bg-white px-3 text-xs font-medium text-slate-500 shadow-sm shadow-slate-950/[0.02] dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none">
          {count}
        </span>
      </div>
      {children}
    </section>
  )
}
