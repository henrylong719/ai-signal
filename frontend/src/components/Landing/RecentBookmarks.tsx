import { SavedArticlesService } from '@/client';
import { isLoggedIn } from '@/hooks/useAuth';
import { Skeleton } from '@/components/ui/skeleton';
import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { BookmarkIcon, ChevronRightIcon } from 'lucide-react';

const RecentBookmarks = () => {
  const loggedIn = isLoggedIn();

  const { data, isLoading } = useQuery({
    queryKey: ['savedArticles'],
    queryFn: () => SavedArticlesService.readSavedArticles({}),
    enabled: loggedIn,
  });

  const articles = data?.data.slice(0, 5) ?? [];

  return (
    <div className="pt-4">
      <Link
        to="/saved-articles"
        className="group flex items-center justify-between py-3 border-b border-slate-100 hover:border-slate-200 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="text-slate-400 group-hover:text-slate-900 transition-colors">
            <BookmarkIcon className="w-5 h-5 stroke-[1.5]" />
          </div>
          <span className="font-medium text-slate-400 font-sans text-sm">
            Your Saved Articles
          </span>
        </div>
        <ChevronRightIcon className="w-4 h-4 text-slate-300 group-hover:text-slate-900 transition-colors" />
      </Link>
      <div className="space-y-5 mt-2">
        {isLoading
          ? ['a', 'b', 'c'].map((key) => (
              <div key={key} className="flex gap-4 items-start">
                <Skeleton className="h-8 w-6 rounded" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-full rounded" />
                  <Skeleton className="h-3 w-24 rounded" />
                </div>
              </div>
            ))
          : articles.map((article, index) => (
              <div key={article.id} className="group flex gap-4 items-start">
                <span className="font-serif text-2xl font-medium text-slate-200 group-hover:text-slate-300 transition-colors leading-none mt-1">
                  0{index + 1}
                </span>
                <div>
                  <Link to={`/`}>
                    <h4 className="font-serif font-medium text-slate-900 group-hover:text-slate-600 leading-snug mb-1.5">
                      {article.title}
                    </h4>
                  </Link>
                  <div className="text-xs text-slate-400 flex items-center gap-1.5 font-sans">
                    <span className="text-slate-600">{article.source}</span>
                  </div>
                </div>
              </div>
            ))}
      </div>
    </div>
  );
};

export default RecentBookmarks;
