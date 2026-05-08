import { createFileRoute, Link } from '@tanstack/react-router';
import { SavedArticleList } from '@/components/Articles/SavedArticleList';
import { PageContainer, PageHeader } from '@/components/Layout/Page';

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
    <PageContainer variant="default">
      <PageHeader
        eyebrow="Library"
        title="Your library"
        description="Revisit saved articles and use them as taste signals for sharper recommendations."
      >
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
      </PageHeader>
      <SavedArticleList />
    </PageContainer>
  );
}
