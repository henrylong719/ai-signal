import { ArticleList } from '@/components/Articles/ArticleList';
import { useArticleFeed } from '@/hooks/useArticleFeed';
import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/_layout/search-feed/$q')({
  component: SearchFeed,
});

function SearchFeed() {
  const { q } = Route.useParams();

  console.log(q);
  const feed = useArticleFeed({ search: q });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
      <p className="mt-10 text-4xl font-semibold">Results for {q}</p>
      <ArticleList {...feed} />
    </div>
  );
}
