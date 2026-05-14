import { Skeleton } from '../ui/skeleton'

const SOURCE_SKELETON_GROUPS = ['official', 'research', 'media']
const SOURCE_SKELETON_ITEMS = ['first', 'second', 'third', 'fourth']

function SourceGroupSkeleton() {
  return (
    <div className="space-y-8">
      {SOURCE_SKELETON_GROUPS.map((group) => (
        <section key={group}>
          <div className="mb-4 flex items-center gap-2">
            <Skeleton className="h-5 w-28 rounded" />
            <Skeleton className="h-4 w-20 rounded" />
          </div>
          <div className="space-y-3 md:space-y-0 md:divide-y md:divide-slate-200/65 dark:md:divide-border/70">
            {SOURCE_SKELETON_ITEMS.map((item) => (
              <div
                key={`${group}-${item}`}
                className="rounded-2xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.03)] md:-mx-4 md:rounded-lg md:border-0 md:bg-transparent md:px-4 md:py-3.5 md:shadow-none dark:border-border dark:bg-card/35 dark:shadow-none md:dark:bg-transparent"
              >
                <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 md:gap-4">
                  <div className="min-w-0 md:max-w-3xl">
                    <Skeleton className="h-5 w-36 rounded" />
                    <Skeleton className="mt-2 h-4 w-44 rounded" />
                    <Skeleton className="mt-2 h-4 w-full max-w-md rounded" />
                    <Skeleton className="mt-2 h-3 w-24 rounded" />
                  </div>
                  <Skeleton className="h-10 w-24 shrink-0 rounded-full md:h-9 md:w-22" />
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
export default SourceGroupSkeleton
