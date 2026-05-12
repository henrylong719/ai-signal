import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRightIcon,
  CalendarDaysIcon,
  CheckCircle2Icon,
  CheckIcon,
  LibraryIcon,
  SparklesIcon,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import {
  type category as Category,
  type OnboardingComplete,
  UsersService,
} from '@/client'
import { TopicsField } from '@/components/Personalization/TopicsField'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { LoadingButton } from '@/components/ui/loading-button'
import useAuth from '@/hooks/useAuth'
import useCustomToast from '@/hooks/useCustomToast'
import { useInterests } from '@/hooks/useInterests'
import { useSources } from '@/hooks/useSources'
import { cn } from '@/lib/utils'

// Recommended-but-not-required minimums. Soft floors only — the user
// can always advance, but staying under these triggers a small inline
// nudge so people don't blow through the flow without giving the
// recommender enough signal.
const MIN_TOPICS = 3
const MIN_SOURCES = 2
const MAX_SOURCES_VISIBLE = 18

type Step = 0 | 1 | 2 | 3

const STEP_TITLES = [
  'Welcome to AI Signal',
  'Pick a few topics',
  'Choose trusted sources',
  "You're set",
] as const

function detectTimezone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null
  } catch {
    return null
  }
}

/**
 * First-run onboarding modal.
 *
 * Opens automatically for authenticated users whose ``onboarded_at`` is
 * null — that flag lives on the User record so we get exactly-once
 * semantics across devices. Closing the modal in any way (X button,
 * click-outside, finishing the last step) marks it complete; we'd
 * rather show it once and trust the user to find /personalization later
 * than nag them on every session.
 */
export function OnboardingDialog() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const { interests, save: saveInterests } = useInterests()
  const { sources } = useSources()

  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<Step>(0)
  const [topics, setTopics] = useState<Category[]>([])
  const [chosenSources, setChosenSources] = useState<string[]>([])
  const [digestOptIn, setDigestOptIn] = useState(true)

  // Auto-open once per user when their account hasn't been marked
  // onboarded yet. Re-open is suppressed in the same tab session
  // because closing the dialog completes onboarding server-side.
  useEffect(() => {
    if (!user) return
    if (user.onboarded_at) return
    setOpen(true)
  }, [user])

  // When the user already has interests (signed in on another device,
  // skipped onboarding before, etc.) seed the form so we don't blow
  // away their existing choices when they finish the flow.
  useEffect(() => {
    if (!interests) return
    setTopics(interests.categories ?? [])
    setChosenSources(interests.preferred_sources ?? [])
  }, [interests])

  const completeMutation = useMutation({
    mutationFn: (body: OnboardingComplete) =>
      UsersService.completeOnboarding({ requestBody: body }),
    onSuccess: (data) => {
      queryClient.setQueryData(['currentUser'], data)
    },
    onError: () => {
      showErrorToast('Could not save your preferences. Please try again.')
    },
  })

  // Curated 18-source slice, ordered by source-type so the picker
  // shows a representative cross-section without overwhelming. Full
  // catalog stays available in /personalization.
  const featuredSources = useMemo(() => {
    if (!sources?.length) return []
    const order = ['official', 'research', 'newsletter', 'independent']
    return [...sources]
      .sort((a, b) => {
        const ai = order.indexOf(a.source_type)
        const bi = order.indexOf(b.source_type)
        return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
      })
      .slice(0, MAX_SOURCES_VISIBLE)
  }, [sources])

  const toggleSource = (name: string) => {
    setChosenSources((prev) =>
      prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name],
    )
  }

  const finish = () => {
    // Persist interests first (preferred_sources + categories) so the
    // For-You feed can use them as soon as the modal closes. Tags stay
    // empty here — they're a power-user signal best added on the
    // personalization page, not at first run.
    saveInterests(
      {
        categories: topics,
        tags: interests?.tags ?? [],
        preferred_sources: chosenSources,
      },
      { successMessage: 'Your preferences are saved.' },
    )
    completeMutation.mutate(
      {
        timezone: detectTimezone(),
        daily_digest_enabled: digestOptIn,
      },
      {
        onSuccess: () => setOpen(false),
      },
    )
  }

  const handleOpenChange = (next: boolean) => {
    if (!next && open) {
      // Closing without finishing should still mark the user as
      // onboarded — otherwise the modal reopens on every session
      // until they finish, which is annoying. We persist whatever
      // state they've already entered (topics, sources) but skip
      // the digest opt-in since they didn't get to that step.
      if (!user?.onboarded_at) {
        if (topics.length || chosenSources.length) {
          saveInterests({
            categories: topics,
            tags: interests?.tags ?? [],
            preferred_sources: chosenSources,
          })
        }
        completeMutation.mutate({
          timezone: detectTimezone(),
          daily_digest_enabled: false,
        })
      }
    }
    setOpen(next)
  }

  if (!user) return null

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        showCloseButton
        className="z-[80] max-h-[calc(100svh-2rem)] gap-0 overflow-y-auto border border-slate-200/80 bg-white p-0 text-slate-950 shadow-xl sm:max-w-[640px] sm:rounded-xl dark:border-border dark:bg-card dark:text-card-foreground"
      >
        <DialogTitle className="sr-only">{STEP_TITLES[step]}</DialogTitle>
        <DialogDescription className="sr-only">
          A short setup so AI Signal can shape your feed and digest.
        </DialogDescription>

        <StepIndicator step={step} />

        <div className="px-6 pb-2 pt-5 sm:px-8 sm:pb-3">
          {step === 0 && <WelcomeStep />}
          {step === 1 && <TopicsStep value={topics} onChange={setTopics} />}
          {step === 2 && (
            <SourcesStep
              value={chosenSources}
              onToggle={toggleSource}
              sources={featuredSources}
            />
          )}
          {step === 3 && (
            <PreviewStep
              topicCount={topics.length}
              sourceCount={chosenSources.length}
              digestOptIn={digestOptIn}
              onDigestToggle={setDigestOptIn}
            />
          )}
        </div>

        <Footer
          step={step}
          topicsCount={topics.length}
          sourcesCount={chosenSources.length}
          isSaving={completeMutation.isPending}
          onBack={() => setStep((s) => Math.max(0, (s - 1) as Step) as Step)}
          onNext={() => setStep((s) => Math.min(3, (s + 1) as Step) as Step)}
          onFinish={finish}
          onSkip={() => handleOpenChange(false)}
        />
      </DialogContent>
    </Dialog>
  )
}

// ---------------------------------------------------------------------------

function StepIndicator({ step }: { step: Step }) {
  return (
    <div className="flex items-center gap-1.5 px-6 pt-6 sm:px-8">
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          aria-hidden="true"
          className={cn(
            'h-1 flex-1 rounded-full transition-colors',
            i <= step
              ? 'bg-slate-950 dark:bg-foreground'
              : 'bg-slate-200 dark:bg-border',
          )}
        />
      ))}
    </div>
  )
}

function WelcomeStep() {
  return (
    <div className="space-y-5">
      <div className="inline-flex items-center gap-2 rounded-full border border-slate-200/75 bg-slate-50/60 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:border-border dark:bg-muted/35 dark:text-muted-foreground">
        <SparklesIcon className="h-3.5 w-3.5 stroke-[1.8]" aria-hidden="true" />
        AI Signal
      </div>
      <h2 className="font-display text-3xl font-semibold leading-[1.08] tracking-tight text-slate-950 sm:text-4xl dark:text-foreground">
        Let&apos;s tune your signal.
      </h2>
      <p className="max-w-xl text-base leading-7 text-slate-600 dark:text-muted-foreground">
        Three quick choices to shape what AI Signal shows you. Skip anytime and
        refine later from the personalization page.
      </p>
      <ul className="grid gap-3 pt-1 sm:grid-cols-3">
        <Bullet
          icon={CheckCircle2Icon}
          title="Pick topics"
          body="The areas you never want to miss."
        />
        <Bullet
          icon={LibraryIcon}
          title="Choose sources"
          body="Labs and writers you already trust."
        />
        <Bullet
          icon={CalendarDaysIcon}
          title="Daily digest"
          body="Optional 6 am email summary."
        />
      </ul>
    </div>
  )
}

function Bullet({
  icon: Icon,
  title,
  body,
}: {
  icon: typeof CheckCircle2Icon
  title: string
  body: string
}) {
  return (
    <li className="flex flex-col gap-1.5 rounded-lg border border-slate-200/80 bg-white px-3 py-3 dark:border-border dark:bg-card/45">
      <Icon
        className="h-4 w-4 stroke-[1.7] text-slate-500 dark:text-muted-foreground"
        aria-hidden="true"
      />
      <p className="text-sm font-semibold text-slate-950 dark:text-foreground">
        {title}
      </p>
      <p className="text-xs leading-5 text-slate-500 dark:text-muted-foreground">
        {body}
      </p>
    </li>
  )
}

function TopicsStep({
  value,
  onChange,
}: {
  value: Category[]
  onChange: (next: Category[]) => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-muted-foreground">
          Step 1 of 3
        </p>
        <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl dark:text-foreground">
          Pick {MIN_TOPICS} or more topics.
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
          These are the broad signals AI Signal listens for. You can always add
          more later.
        </p>
      </div>
      <TopicsField value={value} onChange={onChange} />
    </div>
  )
}

function SourcesStep({
  value,
  onToggle,
  sources,
}: {
  value: string[]
  onToggle: (name: string) => void
  sources: ReturnType<typeof useSources>['sources']
}) {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-muted-foreground">
          Step 2 of 3
        </p>
        <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl dark:text-foreground">
          Choose {MIN_SOURCES} or more sources you trust.
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
          Followed sources get extra weight in your For You feed and are
          highlighted in the daily digest.
        </p>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2">
        {sources.map((source) => {
          const selected = value.includes(source.name)
          return (
            <li key={source.name}>
              <button
                type="button"
                onClick={() => onToggle(source.name)}
                aria-pressed={selected}
                className={cn(
                  'flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
                  selected
                    ? 'border-slate-950 bg-slate-950 text-white dark:border-primary dark:bg-primary dark:text-primary-foreground'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50 dark:border-border dark:bg-card/45 dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent',
                )}
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold">
                    {source.name}
                  </span>
                  <span
                    className={cn(
                      'mt-0.5 block truncate text-xs',
                      selected
                        ? 'text-white/75 dark:text-primary-foreground/80'
                        : 'text-slate-500 dark:text-muted-foreground',
                    )}
                  >
                    {source.topic}
                  </span>
                </span>
                <span
                  aria-hidden="true"
                  className={cn(
                    'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                    selected
                      ? 'border-white/45 bg-white/10 dark:border-primary-foreground/45 dark:bg-primary-foreground/10'
                      : 'border-slate-300 bg-white dark:border-border dark:bg-background/20',
                  )}
                >
                  <CheckIcon
                    className={cn(
                      'h-3.5 w-3.5 stroke-[2]',
                      selected ? 'opacity-100' : 'opacity-0',
                    )}
                  />
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function PreviewStep({
  topicCount,
  sourceCount,
  digestOptIn,
  onDigestToggle,
}: {
  topicCount: number
  sourceCount: number
  digestOptIn: boolean
  onDigestToggle: (value: boolean) => void
}) {
  const tzLabel = useMemo(() => detectTimezone() ?? 'UTC', [])
  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-muted-foreground">
          Step 3 of 3
        </p>
        <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl dark:text-foreground">
          You&apos;re ready.
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
          AI Signal has{' '}
          <span className="font-semibold text-slate-950 dark:text-foreground">
            {topicCount} topic{topicCount === 1 ? '' : 's'}
          </span>{' '}
          and{' '}
          <span className="font-semibold text-slate-950 dark:text-foreground">
            {sourceCount} source{sourceCount === 1 ? '' : 's'}
          </span>{' '}
          to start with. Your For You feed will calibrate within a few visits.
        </p>
      </div>
      <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200/80 bg-white p-4 transition-colors hover:border-slate-300 hover:bg-slate-50/60 dark:border-border dark:bg-card/45 dark:hover:border-foreground/18 dark:hover:bg-accent/45">
        <input
          type="checkbox"
          checked={digestOptIn}
          onChange={(e) => onDigestToggle(e.target.checked)}
          className="mt-1 h-4 w-4 rounded border-slate-300 text-slate-950 focus:ring-slate-950/15 dark:border-border dark:bg-muted dark:text-foreground dark:focus:ring-ring/35"
        />
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2 text-sm font-semibold text-slate-950 dark:text-foreground">
            <CalendarDaysIcon
              className="h-4 w-4 stroke-[1.8]"
              aria-hidden="true"
            />
            Send me the daily digest at 6 am
          </span>
          <span className="mt-1 block text-xs leading-5 text-slate-500 dark:text-muted-foreground">
            One email per day, grouped by signal area, in your local time (
            {tzLabel}). Unsubscribe anytime.
          </span>
        </span>
      </label>
    </div>
  )
}

function Footer({
  step,
  topicsCount,
  sourcesCount,
  isSaving,
  onBack,
  onNext,
  onFinish,
  onSkip,
}: {
  step: Step
  topicsCount: number
  sourcesCount: number
  isSaving: boolean
  onBack: () => void
  onNext: () => void
  onFinish: () => void
  onSkip: () => void
}) {
  const minNotMet =
    (step === 1 && topicsCount < MIN_TOPICS) ||
    (step === 2 && sourcesCount < MIN_SOURCES)
  const helper =
    step === 1
      ? `${topicsCount} of ${MIN_TOPICS}+ topics`
      : step === 2
        ? `${sourcesCount} of ${MIN_SOURCES}+ sources`
        : ''

  return (
    <div className="mt-4 flex flex-col gap-3 border-t border-slate-200/70 px-6 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-8 dark:border-border">
      <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-muted-foreground">
        {helper && (
          <span
            className={cn(
              'inline-flex items-center rounded-full border px-2.5 py-1 font-medium',
              minNotMet
                ? 'border-slate-200 bg-slate-50 text-slate-500 dark:border-border dark:bg-muted/30 dark:text-muted-foreground'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-950/20 dark:text-emerald-300',
            )}
          >
            {helper}
          </span>
        )}
        {step < 3 && (
          <button
            type="button"
            onClick={onSkip}
            className="rounded-sm font-medium underline-offset-4 hover:text-slate-950 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:hover:text-foreground"
          >
            Skip for now
          </button>
        )}
      </div>
      <div className="flex items-center gap-2">
        {step > 0 && (
          <button
            type="button"
            onClick={onBack}
            className="inline-flex h-10 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-muted/45 dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground"
          >
            Back
          </button>
        )}
        {step < 3 ? (
          <button
            type="button"
            onClick={onNext}
            className="inline-flex h-10 items-center gap-1.5 rounded-full bg-slate-950 px-5 text-sm font-semibold text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92"
          >
            Continue
            <ArrowRightIcon
              className="h-4 w-4 stroke-[1.8]"
              aria-hidden="true"
            />
          </button>
        ) : (
          <LoadingButton
            onClick={onFinish}
            loading={isSaving}
            className="inline-flex h-10 items-center rounded-full bg-slate-950 px-5 text-sm font-semibold text-white hover:bg-slate-800 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92"
          >
            Finish
          </LoadingButton>
        )}
      </div>
    </div>
  )
}
