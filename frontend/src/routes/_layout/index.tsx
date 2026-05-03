import { useInfiniteQuery } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';
import { useEffect, useRef } from 'react';
import { type ArticlesPublic, ArticlesService } from '@/client';
import { ArticleCard } from '@/components/Articles/ArticleCard';

const ARTICLES_PAGE_SIZE = 20;

function getArticlesQueryOptions() {
  return {
    queryKey: ['articles'],
    initialPageParam: 0,
    queryFn: ({ pageParam }: { pageParam: number }) =>
      ArticlesService.readArticles({
        skip: pageParam,
        limit: ARTICLES_PAGE_SIZE,
      }),
    getNextPageParam: (
      lastPage: ArticlesPublic,
      allPages: ArticlesPublic[],
    ) => {
      const loadedArticles = allPages.reduce(
        (total, page) => total + page.data.length,
        0,
      );

      return loadedArticles < lastPage.count ? loadedArticles : undefined;
    },
  };
}

export const Route = createFileRoute('/_layout/')({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: 'AI Signal',
      },
    ],
  }),
});

function Dashboard() {
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isError,
    isPending,
    isFetchingNextPage,
  } = useInfiniteQuery(getArticlesQueryOptions());

  const articles = data?.pages.flatMap((page) => page.data) ?? [];
  const feedStatus = isFetchingNextPage
    ? 'Loading more...'
    : !hasNextPage && articles.length > 0
      ? "You're all caught up."
      : !hasNextPage
        ? 'No articles yet.'
        : null;

  useEffect(() => {
    const loadMoreNode = loadMoreRef.current;

    if (!loadMoreNode || !hasNextPage) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isFetchingNextPage) {
          void fetchNextPage();
        }
      },
      { rootMargin: '300px' },
    );

    observer.observe(loadMoreNode);

    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  if (isPending) {
    return (
      <div className="py-8 text-sm text-slate-500">Loading articles...</div>
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
      <div>
        {articles.map((article) => (
          <ArticleCard article={article} key={article.id} />
        ))}
      </div>
      <div
        ref={loadMoreRef}
        className="py-8 text-center text-sm text-slate-500"
      >
        {feedStatus}
      </div>
    </div>
  );
}
