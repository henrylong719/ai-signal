import { useQuery } from '@tanstack/react-query';
import { createFileRoute, Link, Outlet } from '@tanstack/react-router';

import { ArrowRightIcon } from 'lucide-react';
import { useState } from 'react';
import { ArticlesService, type source_type } from '@/client';
import { Skeleton } from '@/components/ui/skeleton';
import { capitalize, cn } from '@/lib/utils';

export const Route = createFileRoute('/_layout/all-article-sources')({
  component: AllArticleSources,
});

export type source_types = 'all' | source_type;

const SOURCE_TYPES: source_types[] = [
  'all',
  'official',
  'independent',
  'research',
  'community',
];

const SOURCE_SKELETON_GROUPS = ['official', 'independent', 'research'];
const SOURCE_SKELETON_ITEMS = ['first', 'second', 'third', 'fourth'];

function SourceGroupSkeleton() {
  return (
    <>
      {SOURCE_SKELETON_GROUPS.map((group) => (
        <section key={group}>
          <div className="mb-6 border-b border-slate-100 pb-2">
            <Skeleton className="h-4 w-28 rounded" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {SOURCE_SKELETON_ITEMS.map((item) => (
              <div
                key={`${group}-${item}`}
                className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 p-4 rounded-xl border border-slate-100"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <Skeleton className="h-5 w-36 rounded" />
                    <Skeleton className="h-5 w-20 rounded" />
                    <Skeleton className="h-5 w-24 rounded" />
                  </div>
                  <Skeleton className="h-4 w-full max-w-md rounded" />
                </div>
                <Skeleton className="hidden sm:block h-8 w-8 shrink-0 rounded-full" />
              </div>
            ))}
          </div>
        </section>
      ))}
    </>
  );
}

function AllArticleSources() {
  const [sourceFilter, setSourceFilter] = useState<source_types>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['articleSources'],
    queryFn: () => ArticlesService.readSources(),
  });

  const filteredSources =
    sourceFilter === 'all'
      ? data?.data
      : data?.data.filter((s) => s.source_type === sourceFilter);

  const groups = SOURCE_TYPES.filter((type) => type !== 'all')
    .map((type) => {
      return {
        type,
        items: filteredSources?.filter((s) => s.source_type === type),
      };
    })
    .filter((group) => (group?.items || []).length > 0);

  const handleFilterClick = (type: source_types) => {
    setSourceFilter(type);
  };

  return (
    <div className="w-full bg-white pb-24">
      {/* Compact Page Header */}
      <header className="px-4 sm:px-6 lg:px-8 pt-12 pb-8">
        <div>
          <h1 className="font-serif text-3xl sm:text-4xl font-medium text-slate-900 mb-3 tracking-tight">
            Sources
          </h1>
          <p className="text-lg text-slate-500 leading-relaxed font-serif">
            Explore the official publications, research feeds, independent
            writers, and community sites behind AI Signal.
          </p>
        </div>

        {/* Source Type Filters */}
        <div className="flex flex-wrap gap-2 mt-8">
          {SOURCE_TYPES.map((type) => (
            <button
              type="button"
              key={type}
              onClick={() => handleFilterClick(type)}
              className={cn(
                'px-3 py-1.5 rounded-full text-sm font-medium transition-colors border',
                sourceFilter === type
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50',
              )}
            >
              {capitalize(type)}
            </button>
          ))}
        </div>
      </header>

      {/* Main Content Organized by Group */}
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="space-y-16">
          {isLoading ? (
            <SourceGroupSkeleton />
          ) : (
            groups.map(
              (group) =>
                group.items && (
                  <section key={group.type}>
                    <h2 className="font-sans text-sm font-semibold uppercase tracking-widest text-slate-400 mb-6 pb-2 border-b border-slate-100">
                      {group.type}
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {group?.items.map((source) => (
                        <Link
                          key={source.name}
                          to="/article-sources/$s"
                          params={{ s: source.name }}
                        >
                          <div
                            key={source.name}
                            className="group flex flex-col sm:flex-row sm:items-start justify-between gap-4 p-4 rounded-xl border border-transparent hover:border-slate-200 hover:bg-slate-50 hover:shadow-sm transition-all cursor-pointer"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex flex-wrap items-center gap-2 mb-2">
                                <h3 className="font-medium text-slate-900 font-sans text-base">
                                  {source.name}
                                </h3>
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-slate-100 text-slate-500">
                                  {source.source_type}
                                </span>
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider border border-slate-200 text-slate-500">
                                  {source.topic}
                                </span>
                              </div>
                              <p className="text-sm text-slate-500 font-serif leading-relaxed line-clamp-1">
                                {source.description}
                              </p>
                            </div>
                            <div className="hidden sm:flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-white border border-slate-100 shadow-sm opacity-0 group-hover:opacity-100 transition-opacity">
                              <ArrowRightIcon className="w-4 h-4 text-slate-400 group-hover:text-slate-900 transition-colors" />
                            </div>
                          </div>
                        </Link>
                      ))}
                    </div>
                  </section>
                ),
            )
          )}
        </div>
      </div>
      <Outlet />
    </div>
  );
}
