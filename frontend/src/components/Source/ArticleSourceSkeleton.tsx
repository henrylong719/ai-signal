import { ArticleCardSkeleton } from '../Articles/ArticleCardSkeleton'
import { PageContainer } from '../Layout/Page'
import { Skeleton } from '../ui/skeleton'

function ArticleSourceSkeleton() {
  return (
    <PageContainer variant="default">
      <header className="mb-7 border-b border-slate-200/80 pb-7 dark:border-border">
        <Skeleton className="h-9 w-32 rounded-md" />
        <div className="mt-8 max-w-2xl">
          <Skeleton className="h-4 w-24 rounded" />
          <Skeleton className="mt-4 h-10 w-72 max-w-full rounded" />
          <Skeleton className="mt-3 h-5 w-full max-w-xl rounded" />
        </div>
      </header>

      <div className="rounded-lg border border-slate-200/80 bg-white px-5 sm:px-6 dark:border-border dark:bg-card/35">
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
      </div>
    </PageContainer>
  )
}

export default ArticleSourceSkeleton
