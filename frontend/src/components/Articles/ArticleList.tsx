import type { ArticlePublic } from '@/client';
import { ArticleCard } from './ArticleCard';
import { ArticleCardSkeleton } from './ArticleCardSkeleton';

interface ArticleListProps {
  articles: ArticlePublic[];
  feedStatus: string | null;
  loadMoreRef: (node: HTMLDivElement | null) => void;
  isPending: boolean;
  isError: boolean;
}

export function ArticleList({
  articles,
  feedStatus,
  loadMoreRef,
  isPending,
  isError,
}: ArticleListProps) {
  if (isPending) {
    return (
      <div className="py-8">
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-8 text-sm text-slate-500">
        Could not load articles.
      </div>
    );
  }

  return (
    <div>
      {articles.map((article) => (
        <ArticleCard article={article} key={article.id} />
      ))}
      <div
        ref={loadMoreRef}
        className="py-8 text-center text-sm text-slate-500"
      >
        {feedStatus}
      </div>
    </div>
  );
}
