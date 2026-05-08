import {
  createFileRoute,
  Link,
  Outlet,
  useLocation,
} from '@tanstack/react-router';
import {
  AlertCircleIcon,
  CheckIcon,
  PlusIcon,
  RadioTowerIcon,
} from 'lucide-react';
import { useLayoutEffect, useRef, useState } from 'react';
import type { SourcePublic, source_type } from '@/client';
import { ArticleListState } from '@/components/Articles/ArticleList';
import AuthModal from '@/components/Auth/AuthModal';
import { PageContainer, PageHeader } from '@/components/Layout/Page';
import { Skeleton } from '@/components/ui/skeleton';
import { useInterests } from '@/hooks/useInterests';
import { useSources } from '@/hooks/useSources';
import { isLoggedIn } from '@/lib/auth-state';
import { cn } from '@/lib/utils';

export const Route = createFileRoute('/_layout/all-article-sources')({
  component: AllArticleSources,
});

export type source_types = 'all' | source_type;

const SOURCE_TYPES: source_types[] = [
  'all',
  'official',
  'research',
  'analysis',
  'policy',
  'education',
  'papers',
  'media',
  'newsletter',
  'podcast',
  'independent',
  'community',
];

const SOURCE_FILTER_LABELS: Record<source_types, string> = {
  all: 'All',
  official: 'Official',
  research: 'Research',
  analysis: 'Analysis',
  policy: 'Policy',
  education: 'Education',
  papers: 'Papers',
  media: 'Media',
  newsletter: 'Newsletter',
  podcast: 'Podcast',
  independent: 'Independent',
  community: 'Community',
};

const isSourceType = (value: unknown): value is source_types =>
  typeof value === 'string' && SOURCE_TYPES.includes(value as source_types);

const SOURCE_SKELETON_GROUPS = ['official', 'research', 'media'];
const SOURCE_SKELETON_ITEMS = ['first', 'second', 'third', 'fourth'];

const getSourceCountLabel = (count: number) =>
  `${count} ${count === 1 ? 'source' : 'sources'}`;

interface SourceFilterBarProps {
  selected: source_types;
  onSelect: (type: source_types) => void;
}

function SourceFilterBar({ selected, onSelect }: SourceFilterBarProps) {
  return (
    <div className="mb-9 rounded-2xl border border-slate-200/80 bg-slate-50/60 p-2 shadow-[0_1px_2px_rgba(15,23,42,0.03)] dark:border-border dark:bg-card/25 dark:shadow-none">
      <fieldset className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <legend className="sr-only">Filter sources by type</legend>
        {SOURCE_TYPES.map((type) => (
          <button
            type="button"
            key={type}
            onClick={() => onSelect(type)}
            aria-pressed={selected === type}
            className={cn(
              'h-9 shrink-0 rounded-full border px-3.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
              selected === type
                ? 'border-slate-950 bg-slate-950 text-white shadow-sm dark:border-primary dark:bg-primary dark:text-primary-foreground'
                : 'border-slate-200/90 bg-white/90 text-slate-600 shadow-sm shadow-slate-950/[0.02] hover:border-slate-300 hover:bg-white hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent/70 dark:hover:text-foreground',
            )}
          >
            {SOURCE_FILTER_LABELS[type]}
          </button>
        ))}
      </fieldset>
    </div>
  );
}

function SourceGroupSkeleton() {
  return (
    <div className="space-y-10">
      {SOURCE_SKELETON_GROUPS.map((group) => (
        <section key={group}>
          <div className="mb-4 flex items-center gap-2 px-1">
            <Skeleton className="h-5 w-28 rounded" />
            <Skeleton className="h-4 w-20 rounded" />
          </div>
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {SOURCE_SKELETON_ITEMS.map((item) => (
              <div
                key={`${group}-${item}`}
                className="min-h-[11.25rem] rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] dark:border-border dark:bg-card/35 dark:shadow-none"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <Skeleton className="mb-2 h-5 w-36 rounded" />
                    <Skeleton className="h-5 w-28 rounded-full" />
                  </div>
                  <Skeleton className="h-8 w-24 shrink-0 rounded-full" />
                </div>
                <Skeleton className="mt-5 h-4 w-full max-w-md rounded" />
                <Skeleton className="mt-3 h-4 w-3/4 rounded" />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
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

function AllArticleSources() {
  const location = useLocation();
  const savedRouteState = location.state as {
    allArticleSourcesFilter?: unknown;
    allArticleSourcesScrollY?: unknown;
  };
  const [sourceFilter, setSourceFilter] = useState<source_types>(() =>
    isSourceType(savedRouteState.allArticleSourcesFilter)
      ? savedRouteState.allArticleSourcesFilter
      : 'all',
  );
  const [updatingSource, setUpdatingSource] = useState<string | null>(null);
  const hasRestoredScroll = useRef(false);
  const userIsLoggedIn = isLoggedIn();

  const { sources, isLoading, isError } = useSources();
  const {
    interests,
    isLoading: interestsLoading,
    isError: interestsError,
    save,
    isSaving,
  } = useInterests();

  const savedScrollY = savedRouteState.allArticleSourcesScrollY;

  useLayoutEffect(() => {
    if (
      hasRestoredScroll.current ||
      isLoading ||
      typeof savedScrollY !== 'number'
    ) {
      return;
    }

    hasRestoredScroll.current = true;
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: savedScrollY });
    });
  }, [isLoading, savedScrollY]);

  const filteredSources =
    sourceFilter === 'all'
      ? sources
      : sources.filter((source) => source.source_type === sourceFilter);

  const groups = SOURCE_TYPES.filter(
    (type): type is source_type => type !== 'all',
  )
    .map((type) => ({
      type,
      items: filteredSources.filter((source) => source.source_type === type),
    }))
    .filter((group) => group.items.length > 0);

  const sourceCount = sources.length;
  const preferredSources = interests?.preferred_sources ?? [];
  const followDisabled = interestsLoading || interestsError || isSaving;

  const togglePreferredSource = (sourceName: string) => {
    if (!userIsLoggedIn || interestsLoading || interestsError) {
      return;
    }

    const isRemovingSource = preferredSources.includes(sourceName);
    const nextPreferredSources = isRemovingSource
      ? preferredSources.filter((source) => source !== sourceName)
      : [...preferredSources, sourceName];

    setUpdatingSource(sourceName);
    save(
      {
        categories: interests?.categories ?? [],
        tags: interests?.tags ?? [],
        preferred_sources: nextPreferredSources,
      },
      {
        successMessage: isRemovingSource
          ? `${sourceName} removed from your followed sources.`
          : `You're now following ${sourceName}.`,
        onSettled: () => setUpdatingSource(null),
      },
    );
  };

  return (
    <PageContainer variant="wide">
      <PageHeader
        eyebrow="Directory"
        title="Sources"
        description="Explore the labs, research feeds, analysis, policy groups, media outlets, newsletters, podcasts, and community sites behind AI Signal."
        actions={
          <div className="inline-flex max-w-full items-center gap-2 self-start rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm md:self-auto dark:border-border dark:bg-card/35 dark:text-muted-foreground dark:shadow-none">
            <RadioTowerIcon className="h-4 w-4 stroke-[1.8] text-slate-400 dark:text-muted-foreground" />
            <span>
              {isLoading ? 'Loading sources' : getSourceCountLabel(sourceCount)}
            </span>
          </div>
        }
      />

      <SourceFilterBar selected={sourceFilter} onSelect={setSourceFilter} />

      <div className="space-y-10">
        {isLoading ? (
          <SourceGroupSkeleton />
        ) : isError ? (
          <ArticleListState
            title="Could not load sources"
            description="Please refresh the page or try again in a moment."
            icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
          />
        ) : groups.length === 0 ? (
          <ArticleListState
            title={
              sourceFilter === 'all'
                ? 'No sources yet'
                : `No ${SOURCE_FILTER_LABELS[sourceFilter]} sources yet`
            }
            description="Sources will appear here as soon as they are available."
            action={
              sourceFilter !== 'all' && (
                <button
                  type="button"
                  onClick={() => setSourceFilter('all')}
                  className="inline-flex h-9 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-foreground/86 dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Show all sources
                </button>
              )
            }
          />
        ) : (
          groups.map((group) => (
            <SourceSection
              key={group.type}
              type={group.type}
              items={group.items}
              sourceFilter={sourceFilter}
              preferredSources={preferredSources}
              updatingSource={updatingSource}
              isSaving={isSaving}
              followDisabled={followDisabled}
              userIsLoggedIn={userIsLoggedIn}
              onTogglePreferredSource={togglePreferredSource}
            />
          ))
        )}
      </div>
      <Outlet />
    </PageContainer>
  );
}
