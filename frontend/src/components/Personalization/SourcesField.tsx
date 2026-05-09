import { CheckIcon, ChevronDownIcon, XIcon } from 'lucide-react';
import { useId, useState } from 'react';

import type { SourcePublic } from '@/client';
import { Skeleton } from '@/components/ui/skeleton';
import { useSources } from '@/hooks/useSources';
import { cn } from '@/lib/utils';

interface SourcesFieldProps {
  value: string[];
  onChange: (next: string[]) => void;
}

// Group label overrides for source_type values that look terse on screen.
// The Literal in the API uses these short codes; mapping to readable labels
// here keeps the API stable while presenting nicely.
const SOURCE_TYPE_LABELS: Record<SourcePublic['source_type'], string> = {
  official: 'AI Labs',
  research: 'Research',
  analysis: 'Analysis',
  policy: 'Policy',
  education: 'Education',
  papers: 'Paper feeds',
  independent: 'Independent voices',
  community: 'Community',
  newsletter: 'Newsletters',
  podcast: 'Podcasts',
  media: 'Media',
};

// Display order for source_type groups. Anything not listed sorts to the
// end (alphabetical fallback).
const SOURCE_TYPE_ORDER: SourcePublic['source_type'][] = [
  'official',
  'research',
  'analysis',
  'policy',
  'education',
  'papers',
  'newsletter',
  'podcast',
  'media',
  'independent',
  'community',
];

/**
 * Multi-select picker for explicitly preferred article sources.
 *
 * Source list is fetched from the backend (single source of truth) and
 * grouped by `source_type` so AI labs / research orgs / independent voices
 * are visually distinct. Within each group, sources are sorted
 * alphabetically by name.
 *
 * The selection is stored as an array of source `name` strings — the
 * backend uses the display name as the canonical identifier, so we don't
 * introduce a slug layer on the frontend.
 */
export function SourcesField({ value, onChange }: SourcesFieldProps) {
  const { sources, isLoading, isError } = useSources();
  const sourceLibraryId = useId();
  const [isLibraryOpen, setIsLibraryOpen] = useState(false);

  if (isLoading) {
    return <SourcesFieldSkeleton />;
  }

  if (isError) {
    return (
      <p className="text-sm text-slate-500 dark:text-muted-foreground">
        Could not load sources right now. Refresh the page to try again.
      </p>
    );
  }

  const toggle = (name: string) => {
    onChange(
      value.includes(name) ? value.filter((s) => s !== name) : [...value, name],
    );
  };

  // Group sources by source_type, then sort alphabetically by name within
  // each group. Groups themselves render in SOURCE_TYPE_ORDER.
  const grouped = new Map<SourcePublic['source_type'], SourcePublic[]>();
  for (const source of sources) {
    const list = grouped.get(source.source_type) ?? [];
    list.push(source);
    grouped.set(source.source_type, list);
  }
  for (const list of grouped.values()) {
    list.sort((a, b) => a.name.localeCompare(b.name));
  }

  const orderedGroups = [
    ...SOURCE_TYPE_ORDER.filter((t) => grouped.has(t)),
    ...Array.from(grouped.keys())
      .filter((t) => !SOURCE_TYPE_ORDER.includes(t))
      .sort(),
  ];

  const sourceLibraryLabel = isLibraryOpen
    ? 'Hide source library'
    : value.length > 0
      ? 'Edit source picks'
      : 'Browse source library';

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          {value.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {value.map((sourceName) => (
                <button
                  type="button"
                  key={sourceName}
                  onClick={() => toggle(sourceName)}
                  aria-pressed={true}
                  aria-label={`${sourceName} selected. Press to remove.`}
                  className={cn(
                    'inline-flex min-h-9 max-w-full items-center gap-1.5 rounded-full border border-slate-950 bg-slat-950 px-3 py-1.5 text-sm font-medium leading-snug text-white shadow-sm shadow-slate-950/10 transition-all hover:bg-slate-800',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 dark:border-primary dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/88 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
                  )}
                >
                  <span className="wrap-break-word">{sourceName}</span>
                  <XIcon className="h-3.5 w-3.5 shrink-0" />
                </button>
              ))}
            </div>
          ) : (
            <p className="max-w-xl text-sm leading-6 text-slate-500 dark:text-muted-foreground">
              Sources are optional. Add a few when certain labs, journals, or
              newsletters should carry extra weight in your feed.
            </p>
          )}
        </div>

        <button
          type="button"
          aria-expanded={isLibraryOpen}
          aria-controls={sourceLibraryId}
          onClick={() => setIsLibraryOpen((open) => !open)}
          className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm shadow-slate-950/[0.02] transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 dark:border-border dark:bg-transparent dark:text-foreground/86 dark:shadow-none dark:hover:bg-accent dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
        >
          {sourceLibraryLabel}
          <ChevronDownIcon
            className={cn(
              'h-4 w-4 transition-transform',
              isLibraryOpen && 'rotate-180',
            )}
          />
        </button>
      </div>

      {isLibraryOpen && (
        <div
          id={sourceLibraryId}
          className="space-y-7 border-t border-slate-200/70 pt-5 dark:border-border"
        >
          {orderedGroups.map((groupType) => {
            const groupSources = grouped.get(groupType) ?? [];
            if (groupSources.length === 0) return null;
            return (
              <div key={groupType}>
                <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400 dark:text-muted-foreground">
                  {SOURCE_TYPE_LABELS[groupType] ?? groupType}
                </h4>
                <div className="flex flex-wrap gap-2">
                  {groupSources.map((source) => {
                    const selected = value.includes(source.name);
                    return (
                      <button
                        type="button"
                        key={source.name}
                        onClick={() => toggle(source.name)}
                        aria-pressed={selected}
                        className={cn(
                          'inline-flex min-h-10 max-w-full items-center gap-1.5 rounded-full border px-3.5 py-2 text-sm font-medium leading-snug transition-all',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
                          selected
                            ? 'border-slate-950 bg-slate-950 text-white shadow-sm shadow-slate-950/10 hover:bg-slate-800 dark:border-primary dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/88'
                            : 'border-slate-200 bg-white text-slate-600 shadow-sm shadow-slate-950/[0.02] hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground',
                        )}
                      >
                        <CheckIcon
                          className={cn(
                            'h-3.5 w-3.5 shrink-0 transition-opacity',
                            selected ? 'opacity-100' : 'opacity-0',
                          )}
                        />
                        <span className="break-words">{source.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SourcesFieldSkeleton() {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <Skeleton className="h-5 w-full max-w-md" />
      <Skeleton className="h-10 w-44 rounded-full" />
    </div>
  );
}
