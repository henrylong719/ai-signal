import { createFileRoute, Outlet, useLocation } from '@tanstack/react-router';
import { AlertCircleIcon, RadioTowerIcon } from 'lucide-react';
import { useLayoutEffect, useRef, useState } from 'react';
import type { source_type } from '@/client';
import { ArticleListState } from '@/components/Articles/ArticleList';
import { PageContainer, PageHeader } from '@/components/Layout/Page';
import { Skeleton } from '@/components/ui/skeleton';
import { useInterests } from '@/hooks/useInterests';
import { useSources } from '@/hooks/useSources';
import { isLoggedIn } from '@/lib/auth-state';
import { cn } from '@/lib/utils';
import SourceSection from '@/components/Source/SourceSection';
import {
  SOURCE_FILTER_LABELS,
  type source_types,
  SOURCE_TYPES,
} from '@/lib/constants';

export const Route = createFileRoute('/_layout/all-article-sources')({
  component: AllArticleSources,
});

const getSourceCountLabel = (count: number) =>
  `${count} ${count === 1 ? 'source' : 'sources'}`;

const isSourceType = (value: unknown): value is source_types =>
  typeof value === 'string' && SOURCE_TYPES.includes(value as source_types);

const SOURCE_SKELETON_GROUPS = ['official', 'research', 'media'];
const SOURCE_SKELETON_ITEMS = ['first', 'second', 'third', 'fourth'];

interface SourceFilterBarProps {
  selected: source_types;
  onSelect: (type: source_types) => void;
}

function SourceFilterBar({ selected, onSelect }: SourceFilterBarProps) {
  return (
    <div className="sticky top-16 z-40 -mx-4 mb-6 overflow-x-auto border-y border-slate-200/80 bg-white/95 px-4 py-2.5 backdrop-blur sm:top-18 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8 dark:border-border dark:bg-background/92 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <fieldset className="flex w-max min-w-full gap-2">
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
                : 'border-slate-200/90 bg-white/90 text-slate-600 shadow-sm shadow-slate-950/2 hover:border-slate-300 hover:bg-white hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent/70 dark:hover:text-foreground',
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
                className="min-h-45 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] dark:border-border dark:bg-card/35 dark:shadow-none"
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
