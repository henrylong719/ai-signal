import { useQuery } from '@tanstack/react-query';
import { SavedArticlesService } from '@/client';
import { ArticleCard } from './ArticleCard';
import { ArticleCardSkeleton } from './ArticleCardSkeleton';
import { useSavedArticles } from '@/hooks/useSavedArticles';
import { isLoggedIn } from '@/hooks/useAuth';
import { Link } from '@tanstack/react-router';

export function SavedArticleList() {
  const { savedArticleIds, toggleSave } = useSavedArticles();
  const loggedIn = isLoggedIn();

  const { data, isPending } = useQuery({
    queryKey: ['savedArticles'],
    queryFn: () => SavedArticlesService.readSavedArticles({}),
    enabled: loggedIn,
  });

  if (!loggedIn) {
    return (
      <div className="py-8 text-sm text-slate-500">
        <Link to="/login" className="text-slate-900 underline">
          Sign in
        </Link>{' '}
        to save articles and see them here.
      </div>
    );
  }

  if (isPending) {
    return (
      <div className="py-8">
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
      </div>
    );
  }

  const articles = data?.data ?? [];

  if (articles.length === 0) {
    return (
      <div className="py-8 text-sm text-slate-500">
        No saved articles yet. Click the bookmark icon on any article to save it.
      </div>
    );
  }

  return (
    <div>
      {articles.map((article) => (
        <ArticleCard
          article={article}
          key={article.id}
          onBookmark={(e) => {
            e.preventDefault();
            toggleSave(article.id);
          }}
          isBookmarked={savedArticleIds.has(article.id)}
        />
      ))}
    </div>
  );
}
