import { Skeleton } from '../ui/skeleton'

function DigestSkeleton() {
  return (
    <div className="space-y-16">
      {['top', 'research'].map((section) => (
        <section key={section}>
          <div className="mb-9 flex items-center gap-4">
            <Skeleton className="h-3 w-24 rounded bg-slate-100 dark:bg-muted" />
            <Skeleton className="h-px flex-1 rounded bg-slate-100 dark:bg-muted" />
          </div>
          <div className="space-y-12">
            {['a', 'b'].map((item) => (
              <div key={item}>
                <Skeleton className="h-7 w-11/12 rounded bg-slate-100 dark:bg-muted" />
                <Skeleton className="mt-4 h-5 w-full rounded bg-slate-100 dark:bg-muted" />
                <Skeleton className="mt-2 h-5 w-4/5 rounded bg-slate-100 dark:bg-muted" />
                <Skeleton className="mt-5 h-4 w-48 rounded bg-slate-100 dark:bg-muted" />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

export default DigestSkeleton
