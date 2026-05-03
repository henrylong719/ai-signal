import { useInfiniteQuery } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';
import { useCallback, useRef, useState } from 'react';
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

type Tab = 'for-you' | 'latest';

function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('latest');
  const observerRef = useRef<IntersectionObserver | null>(null);
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

  const loadMoreRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }

      if (!node || !hasNextPage) return;

      observerRef.current = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting && !isFetchingNextPage) {
            void fetchNextPage();
          }
        },
        { rootMargin: '300px' },
      );

      observerRef.current.observe(node);
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage],
  );

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

  const tabs: { value: Tab; label: string }[] = [
    { value: 'for-you', label: 'For you' },
    { value: 'latest', label: 'Latest' },
  ];

  return (
    <div>
      <div className="border-b border-slate-200 pt-6 sticky top-20 bg-white z-40">
        <div className="flex gap-10">
          {tabs.map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => setActiveTab(tab.value)}
              className={`pb-5 text-sm font-medium transition-colors relative ${
                activeTab === tab.value
                  ? 'text-slate-900'
                  : 'text-slate-400 hover:text-slate-600'
              }`}
            >
              {tab.label}
              {activeTab === tab.value && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-900 rounded-full" />
              )}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'for-you' && (
        <div className="py-8 text-sm text-slate-500">Nothing here yet.</div>
      )}

      {activeTab === 'latest' && (
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
      )}
    </div>
  );
}
