import { createFileRoute } from '@tanstack/react-router'
import { BookmarkIcon } from 'lucide-react'
import { SavedArticleList } from '@/components/Articles/SavedArticleList'

export const Route = createFileRoute('/_layout/saved-articles')({
  component: SavedArticles,
  head: () => ({
    meta: [
      {
        title: 'Your library',
      },
    ],
  }),
})

function SavedArticles() {
  return (
    <div className="mx-auto w-full max-w-5xl pb-16 pt-10 sm:pb-20 sm:pt-12">
      <header className="mb-7 flex flex-col gap-5 border-b border-slate-200/80 pb-7 md:flex-row md:items-end md:justify-between dark:border-border">
        <div className="max-w-2xl">
          <p className="mb-3 text-xs font-semibold uppercase text-slate-500 dark:text-muted-foreground">
            Library
          </p>
          <h1 className="font-display text-3xl font-semibold text-slate-950 sm:text-4xl dark:text-foreground">
            Your library
          </h1>
          <p className="mt-3 max-w-xl text-base leading-7 text-slate-500 dark:text-muted-foreground">
            Revisit saved articles, research notes, and signals worth coming
            back to.
          </p>
        </div>
        <div className="inline-flex max-w-full items-center gap-2 self-start rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 shadow-sm md:self-auto dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none">
          <BookmarkIcon className="h-4 w-4 stroke-[1.8] text-slate-400 dark:text-muted-foreground" />
          Saved articles
        </div>
      </header>
      <div className="max-w-4xl">
        <SavedArticleList />
      </div>
    </div>
  )
}
