import { createFileRoute, Link } from '@tanstack/react-router'
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
    <div className="mx-auto w-full max-w-4xl pb-16 pt-10 sm:pb-20 sm:pt-12">
      <header className="mb-7 border-b border-slate-200/80 pb-7 dark:border-border">
        <div className="max-w-2xl">
          <p className="mb-3 text-xs font-semibold uppercase text-slate-500 dark:text-muted-foreground">
            Library
          </p>
          <h1 className="font-display text-3xl font-semibold text-slate-950 sm:text-4xl dark:text-foreground">
            Your library
          </h1>
          <p className="mt-3 max-w-xl text-base leading-7 text-slate-500 dark:text-muted-foreground">
            Revisit saved articles and use them as taste signals for sharper
            recommendations.
          </p>

          <p className="mt-5 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
            Want sharper recommendations?{' '}
            <Link
              to="/personalization"
              className="font-medium text-slate-800 underline decoration-slate-300 underline-offset-4 transition-colors hover:text-slate-950 hover:decoration-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-foreground/86 dark:decoration-border dark:hover:text-foreground dark:hover:decoration-foreground/45 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
            >
              Tune your signal
            </Link>
            .
          </p>
        </div>
      </header>
      <div>
        <SavedArticleList />
      </div>
    </div>
  )
}
