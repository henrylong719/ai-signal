import { Link } from '@tanstack/react-router';
import { CheckIcon, PlusIcon } from 'lucide-react';
import AuthModal from '../Auth/AuthModal';
import { cn } from '@/lib/utils';
import { SOURCE_FILTER_LABELS, type source_types } from '@/lib/constants';
import type { source_type, SourcePublic } from '@/client';

interface SourceSectionProps {
  type: source_type;
  items: SourcePublic[];
  sourceFilter: source_types;
  preferredSources: string[];
  updatingSource: string | null;
  isSaving: boolean;
  followDisabled: boolean;
  userIsLoggedIn: boolean;
  onTogglePreferredSource: (sourceName: string) => void;
}

const getSourceCountLabel = (count: number) =>
  `${count} ${count === 1 ? 'source' : 'sources'}`;

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
      <div className="mb-4 flex flex-wrap items-baseline gap-x-2 gap-y-1 px-1">
        <h2 className="text-base font-semibold text-slate-950 dark:text-foreground">
          {SOURCE_FILTER_LABELS[type]}
        </h2>
        <span className="text-sm font-medium text-slate-400 dark:text-muted-foreground">
          · {getSourceCountLabel(items.length)}
        </span>
      </div>

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {items.map((source) => {
          const isPreferredSource = preferredSources.includes(source.name);
          const isUpdatingSource = updatingSource === source.name && isSaving;

          return (
            <SourceCard
              key={source.name}
              source={source}
              sourceFilter={sourceFilter}
              userIsLoggedIn={userIsLoggedIn}
              isPreferredSource={isPreferredSource}
              isUpdatingSource={isUpdatingSource}
              followDisabled={followDisabled}
              onTogglePreferredSource={onTogglePreferredSource}
            />
          );
        })}
      </div>
    </section>
  );
}

interface SourceCardProps {
  source: SourcePublic;
  sourceFilter: source_types;
  userIsLoggedIn: boolean;
  isPreferredSource: boolean;
  isUpdatingSource: boolean;
  followDisabled: boolean;
  onTogglePreferredSource: (sourceName: string) => void;
}

function SourceCard({
  source,
  sourceFilter,
  userIsLoggedIn,
  isPreferredSource,
  isUpdatingSource,
  followDisabled,
  onTogglePreferredSource,
}: SourceCardProps) {
  return (
    <article className="group relative min-h-[11.25rem] rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.03)] transition-all hover:-translate-y-0.5 hover:border-slate-300 hover:bg-slate-50/60 hover:shadow-[0_1px_2px_rgba(15,23,42,0.04),0_16px_34px_rgba(15,23,42,0.06)] dark:border-border dark:bg-card/35 dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-card/65 dark:hover:shadow-none">
      <Link
        to="/article-sources/$s"
        params={{ s: source.name }}
        state={(previousState) => ({
          ...previousState,
          allArticleSourcesFilter: sourceFilter,
          allArticleSourcesScrollY: window.scrollY,
        })}
        aria-label={`View ${source.name} source details`}
        className="absolute inset-0 z-10 rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
      />

      <div className="pointer-events-none relative z-20 flex h-full min-h-32 flex-col">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1 pr-1">
            <h3 className="truncate text-base font-semibold text-slate-950 transition-colors group-hover:text-slate-900 dark:text-foreground dark:group-hover:text-foreground">
              {source.name}
            </h3>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <span className="inline-flex max-w-full items-center rounded-full border border-slate-200/90 bg-slate-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:border-border dark:bg-muted/30 dark:text-muted-foreground">
                <span className="truncate">{source.topic}</span>
              </span>
            </div>
          </div>

          <div className="pointer-events-auto relative z-30 flex shrink-0 items-start">
            {userIsLoggedIn ? (
              <button
                type="button"
                onClick={() => onTogglePreferredSource(source.name)}
                disabled={followDisabled}
                aria-pressed={isPreferredSource}
                className={cn(
                  'inline-flex h-8 items-center justify-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-60 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
                  isPreferredSource
                    ? 'border-slate-950 bg-slate-950 text-white shadow-sm dark:border-primary dark:bg-primary dark:text-primary-foreground'
                    : 'border-slate-200 bg-white/90 text-slate-500 shadow-sm shadow-slate-950/[0.02] hover:border-slate-300 hover:bg-white hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:bg-accent dark:hover:text-foreground',
                )}
              >
                {isPreferredSource ? (
                  <CheckIcon className="h-3.5 w-3.5" />
                ) : (
                  <PlusIcon className="h-3.5 w-3.5" />
                )}
                {isUpdatingSource
                  ? 'Saving'
                  : isPreferredSource
                    ? 'Following'
                    : 'Follow'}
              </button>
            ) : (
              <AuthModal
                title={`Sign in to follow ${source.name}`}
                description="Follow trusted sources to shape your personalized AI Signal feed."
                trigger={
                  <button
                    type="button"
                    className="inline-flex h-8 items-center justify-center gap-1.5 rounded-full border border-slate-200 bg-white/90 px-3 text-xs font-medium text-slate-500 shadow-sm shadow-slate-950/[0.02] transition-all hover:border-slate-300 hover:bg-white hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                  >
                    <PlusIcon className="h-3.5 w-3.5" />
                    Follow
                  </button>
                }
              />
            )}
          </div>
        </div>

        <p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
          {source.description}
        </p>
      </div>
    </article>
  );
}

export default SourceSection;
