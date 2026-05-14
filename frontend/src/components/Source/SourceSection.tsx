import { Link } from '@tanstack/react-router'
import { CheckIcon, PlusIcon } from 'lucide-react'
import type { SourcePublic } from '@/client'
import { SOURCE_FILTER_LABELS, type source_types } from '@/lib/constants'
import { cn } from '@/lib/utils'
import AuthModal from '../Auth/AuthModal'

type SourceSectionType = Exclude<source_types, 'all'>

interface SourceSectionProps {
  type: SourceSectionType
  items: SourcePublic[]
  sourceFilter: source_types
  preferredSources: string[]
  updatingSource: string | null
  isSaving: boolean
  followDisabled: boolean
  userIsLoggedIn: boolean
  onTogglePreferredSource: (sourceName: string) => void
}

const getSourceCountLabel = (count: number) =>
  `${count} ${count === 1 ? 'source' : 'sources'}`

type SourceDisplayData = SourcePublic & {
  domain?: string
  url?: string
  website_url?: string
}

const getSourceDomain = (source: SourcePublic) => {
  const displaySource = source as SourceDisplayData
  const sourceDomain = displaySource.domain?.trim()

  if (sourceDomain) {
    return sourceDomain.replace(/^www\./, '')
  }

  const sourceUrl = displaySource.website_url ?? displaySource.url

  if (!sourceUrl) return null

  try {
    return new URL(sourceUrl).hostname.replace(/^www\./, '')
  } catch {
    return null
  }
}

function SourceSection({
  type,
  items,
  sourceFilter,
  preferredSources,
  updatingSource,
  isSaving,
  followDisabled,
  userIsLoggedIn,
  onTogglePreferredSource,
}: SourceSectionProps) {
  return (
    <section className="scroll-mt-28">
      <div className="mb-4 flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <h2 className="text-base font-semibold text-slate-950 dark:text-foreground">
          {SOURCE_FILTER_LABELS[type]}
        </h2>
        <span className="text-sm font-medium text-slate-400 dark:text-muted-foreground">
          · {getSourceCountLabel(items.length)}
        </span>
      </div>

      <div className="space-y-3 md:space-y-0 md:divide-y md:divide-slate-200/65 dark:md:divide-border/70">
        {items.map((source) => {
          const isPreferredSource = preferredSources.includes(source.name)
          const isUpdatingSource = updatingSource === source.name && isSaving

          return (
            <SourceDirectoryItem
              key={source.name}
              source={source}
              sourceFilter={sourceFilter}
              userIsLoggedIn={userIsLoggedIn}
              isPreferredSource={isPreferredSource}
              isUpdatingSource={isUpdatingSource}
              followDisabled={followDisabled}
              onTogglePreferredSource={onTogglePreferredSource}
            />
          )
        })}
      </div>
    </section>
  )
}

interface SourceDirectoryItemProps {
  source: SourcePublic
  sourceFilter: source_types
  userIsLoggedIn: boolean
  isPreferredSource: boolean
  isUpdatingSource: boolean
  followDisabled: boolean
  onTogglePreferredSource: (sourceName: string) => void
}

function SourceDirectoryItem({
  source,
  sourceFilter,
  userIsLoggedIn,
  isPreferredSource,
  isUpdatingSource,
  followDisabled,
  onTogglePreferredSource,
}: SourceDirectoryItemProps) {
  const sourceDomain = getSourceDomain(source)

  return (
    <article className="group relative overflow-hidden rounded-2xl border border-slate-200/75 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.03)] transition-[background-color,border-color,box-shadow] hover:border-slate-300 hover:bg-slate-100/70 focus-within:border-slate-300 focus-within:bg-slate-100/70 md:-mx-4 md:rounded-lg md:border-0 md:bg-transparent md:px-4 md:py-3.5 md:shadow-none md:hover:bg-slate-100/80 md:hover:shadow-[inset_0_0_0_1px_rgba(148,163,184,0.24)] md:focus-within:bg-slate-100/80 md:focus-within:shadow-[inset_0_0_0_1px_rgba(148,163,184,0.24)] dark:border-border dark:bg-card/35 dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-card/60 dark:focus-within:border-foreground/18 dark:focus-within:bg-card/60 md:dark:bg-transparent md:dark:hover:bg-accent/45 md:dark:hover:shadow-none md:dark:focus-within:bg-accent/45 md:dark:focus-within:shadow-none">
      <Link
        to="/article-sources/$s"
        params={{ s: source.name }}
        state={(previousState) => ({
          ...previousState,
          allArticleSourcesFilter: sourceFilter,
          allArticleSourcesScrollY: window.scrollY,
        })}
        aria-label={`View ${source.name} source details`}
        className="absolute inset-0 z-10 rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 md:rounded-lg dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
      />

      <div className="pointer-events-none relative z-20 grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start gap-3 md:gap-4">
        <div className="min-w-0 md:max-w-3xl">
          <h3 className="truncate text-base font-semibold text-slate-950 transition-colors group-hover:text-slate-900 dark:text-foreground dark:group-hover:text-foreground">
            {source.name}
          </h3>
          <p className="mt-1 truncate text-sm text-slate-500 dark:text-muted-foreground">
            {source.topic} · {SOURCE_FILTER_LABELS[source.source_type]}
          </p>
          <p className="mt-2 line-clamp-2 wrap-break-word text-sm leading-6 text-slate-500 md:line-clamp-1 dark:text-muted-foreground">
            {source.description}
          </p>

          {sourceDomain && (
            <p className="mt-2 truncate text-xs font-medium text-slate-400 md:mt-1 dark:text-muted-foreground/80">
              {sourceDomain}
            </p>
          )}
        </div>

        <div className="pointer-events-auto relative z-30 shrink-0">
          <SourceFollowButton
            source={source}
            userIsLoggedIn={userIsLoggedIn}
            isPreferredSource={isPreferredSource}
            isUpdatingSource={isUpdatingSource}
            followDisabled={followDisabled}
            onTogglePreferredSource={onTogglePreferredSource}
          />
        </div>
      </div>
    </article>
  )
}

interface SourceFollowButtonProps {
  source: SourcePublic
  userIsLoggedIn: boolean
  isPreferredSource: boolean
  isUpdatingSource: boolean
  followDisabled: boolean
  onTogglePreferredSource: (sourceName: string) => void
}

function SourceFollowButton({
  source,
  userIsLoggedIn,
  isPreferredSource,
  isUpdatingSource,
  followDisabled,
  onTogglePreferredSource,
}: SourceFollowButtonProps) {
  const buttonClassName = cn(
    'inline-flex h-10 items-center justify-center gap-1.5 whitespace-nowrap rounded-full border px-3 text-xs font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-60 md:h-9 md:px-2.5 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
    isPreferredSource
      ? 'border-slate-950 bg-slate-950 text-white shadow-sm dark:border-foreground dark:bg-foreground dark:text-background'
      : 'border-slate-200 bg-white/90 text-slate-500 shadow-sm shadow-slate-950/2 hover:border-slate-300 hover:bg-white hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:bg-accent dark:hover:text-foreground',
  )

  if (!userIsLoggedIn) {
    return (
      <AuthModal
        title={`Sign in to follow ${source.name}`}
        description="Sign in to save articles, follow trusted sources, and tune your feed."
        trigger={
          <button
            type="button"
            aria-label={`Follow source ${source.name}`}
            className={buttonClassName}
          >
            <PlusIcon className="h-3.5 w-3.5" />
            Follow
          </button>
        }
      />
    )
  }

  return (
    <button
      type="button"
      onClick={() => onTogglePreferredSource(source.name)}
      disabled={followDisabled}
      aria-pressed={isPreferredSource}
      aria-label={
        isPreferredSource
          ? `Unfollow source ${source.name}`
          : `Follow source ${source.name}`
      }
      className={buttonClassName}
    >
      {isPreferredSource ? (
        <CheckIcon className="h-3.5 w-3.5" />
      ) : (
        <PlusIcon className="h-3.5 w-3.5" />
      )}
      {isUpdatingSource ? 'Saving' : isPreferredSource ? 'Following' : 'Follow'}
    </button>
  )
}

export default SourceSection
