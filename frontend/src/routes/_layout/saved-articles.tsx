import { createFileRoute } from '@tanstack/react-router';
import { BookmarkIcon } from 'lucide-react';
import { SavedArticleList } from '@/components/Articles/SavedArticleList';

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
    <div className="mx-auto w-full max-w-5xl pb-16 pt-8 sm:pb-20 sm:pt-10">
      <header className="mb-6 flex flex-col gap-5 border-b border-slate-200/70 pb-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            Library
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Your library
          </h1>
          <p className="mt-3 max-w-xl text-base leading-7 text-slate-500">
            Revisit saved articles, research notes, and signals worth coming
            back to.
          </p>
        </div>
        <div className="inline-flex max-w-full items-center gap-2 self-start rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-500 shadow-sm md:self-auto">
          <BookmarkIcon className="h-4 w-4 stroke-[1.8] text-slate-400" />
          Saved articles
        </div>
      </header>
      <div className="max-w-4xl">
        <SavedArticleList />
      </div>
    </div>
  );
}
