import { Skeleton } from '../ui/skeleton'

function DigestSkeleton() {
  return (
    <div className="space-y-18 md:space-y-22">
      {['top', 'research'].map((section, index) => (
        <section key={section}>
          <div
            className={`border-t border-slate-200/80 pt-8 dark:border-border/80 ${
              index === 0 ? 'border-t-0 pt-0' : ''
            }`}
          >
            <div className="mb-4 flex items-center gap-3">
              <Skeleton className="h-3 w-20 rounded bg-slate-100 dark:bg-muted" />
              <Skeleton className="h-px w-8 rounded bg-slate-100 dark:bg-muted" />
              <Skeleton className="h-3 w-16 rounded bg-slate-100 dark:bg-muted" />
            </div>
            <div className="grid gap-3 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] md:items-end">
              <Skeleton className="h-11 w-56 rounded bg-slate-100 dark:bg-muted" />
              <div>
                <Skeleton className="h-4 w-full max-w-lg rounded bg-slate-100 dark:bg-muted" />
                <Skeleton className="mt-2 h-4 w-3/4 max-w-md rounded bg-slate-100 dark:bg-muted" />
              </div>
            </div>
          </div>

          <div className="mt-7 divide-y divide-slate-200/80 border-y border-slate-200/80 dark:divide-border/80 dark:border-border/80">
            {['a', 'b'].map((item) => (
              <div
                key={item}
                className="flex items-start gap-4 py-7 sm:gap-6 sm:py-8"
              >
                <div className="min-w-0 flex-1">
                  <Skeleton className="h-7 w-11/12 rounded bg-slate-100 dark:bg-muted" />
                  <Skeleton className="mt-4 h-5 w-full rounded bg-slate-100 dark:bg-muted" />
                  <Skeleton className="mt-2 h-5 w-4/5 rounded bg-slate-100 dark:bg-muted" />
                  <Skeleton className="mt-5 h-4 w-48 rounded bg-slate-100 dark:bg-muted" />
                </div>
                <Skeleton className="hidden aspect-4/3 w-36 shrink-0 rounded-lg bg-slate-100 sm:block md:w-44 dark:bg-muted" />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

export default DigestSkeleton
