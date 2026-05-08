import { PageContainer } from '../Layout/Page';
import { Skeleton } from '../ui/skeleton';

function PersonalizationSkeleton() {
  return (
    <PageContainer
      variant="narrow"
      spacing="none"
      className="pb-16 pt-8 sm:pb-20 sm:pt-12"
    >
      <header className="border-b border-slate-200/70 pb-8 dark:border-border">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-5 h-12 w-full max-w-xl" />
        <Skeleton className="mt-4 h-6 w-full max-w-2xl" />
        <Skeleton className="mt-2 h-6 w-full max-w-lg" />
      </header>
      <div className="divide-y divide-slate-200/70 dark:divide-border">
        {[0, 1, 2].map((i) => (
          <section key={i} className="py-8 sm:py-10">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="mt-3 h-7 w-56" />
            <Skeleton className="mt-2 h-4 w-full max-w-md" />
            <div className="mt-6 flex flex-wrap gap-2.5">
              {[0, 1, 2, 3, 4].map((j) => (
                <Skeleton key={j} className="h-11 w-24 rounded-full" />
              ))}
            </div>
          </section>
        ))}
      </div>
    </PageContainer>
  );
}

export default PersonalizationSkeleton;
