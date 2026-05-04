import { useQuery } from '@tanstack/react-query';
import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeftIcon } from 'lucide-react';
import { ArticlesService } from '@/client';
import { ArticleCardSkeleton } from '@/components/Articles/ArticleCardSkeleton';
import { ArticleList } from '@/components/Articles/ArticleList';
import { Skeleton } from '@/components/ui/skeleton';
import { useArticleFeed } from '@/hooks/useArticleFeed';
import { capitalize } from '@/lib/utils';

export const Route = createFileRoute('/_layout/article-sources/$s')({
  component: ArticlesSources,
});

function ArticleSourceSkeleton() {
  return (
    <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
      <header className="pt-12 pb-5 border-b border-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
          <div className="max-w-2xl w-full">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <Skeleton className="h-10 w-56 rounded" />
              <Skeleton className="h-7 w-24 rounded-md" />
              <Skeleton className="h-7 w-28 rounded-md" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-5 w-full max-w-xl rounded" />
              <Skeleton className="h-5 w-3/4 max-w-lg rounded" />
            </div>
          </div>
        </div>
      </header>

      <div className="py-8">
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
      </div>
    </div>
  );
}

function ArticlesSources() {
  const { s } = Route.useParams();

  const feed = useArticleFeed({ source: s });

  const sourcesQuery = useQuery({
    queryKey: ['articleSources'],
    queryFn: () => ArticlesService.readSources(),
  });

  const source = sourcesQuery.data?.data.find((source) => source.name === s);

  if (sourcesQuery.isLoading) {
    return <ArticleSourceSkeleton />;
  }

  if (!source) {
    return (
      <div className="w-full bg-white pb-24 pt-20 text-center">
        <h1 className="text-2xl font-serif text-slate-900 mb-4">
          Source not found
        </h1>
        <Link
          to="/all-article-sources"
          className="text-sm text-slate-500 hover:text-slate-900 inline-flex items-center"
        >
          <ArrowLeftIcon className="w-4 h-4 mr-2" /> Back to sources
        </Link>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
      <header className="pt-12 pb-5 border-b border-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
          <div className="">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <h1 className="font-serif text-3xl sm:text-4xl font-medium text-slate-900 tracking-tight">
                {capitalize(source.name)}
              </h1>
              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium uppercase tracking-wider bg-slate-100 text-slate-600">
                {capitalize(source.source_type)}
              </span>
              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium uppercase tracking-wider border border-slate-200 text-slate-600">
                {capitalize(source.topic)}
              </span>
            </div>
            <p className="text-lg text-slate-500 leading-relaxed font-serif">
              {capitalize(source.description)}
            </p>
          </div>
        </div>
      </header>

      <ArticleList {...feed} />
    </div>
  );
}
