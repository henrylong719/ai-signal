import { SavedArticleList } from '@/components/Articles/SavedArticleList';
import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/_layout/saved-articles')({
  component: SavedArticles,
  head: () => ({
    meta: [
      {
        title: 'Your library',
      },
    ],
  }),
});

function SavedArticles() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex-auto md:flex-5">
      <p className="mt-10 text-4xl font-semibold"> Your Library</p>
      <SavedArticleList />
    </div>
  );
}
