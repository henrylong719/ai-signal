import { Skeleton } from '../ui/skeleton';

const SOURCE_SKELETON_GROUPS = ['official', 'research', 'media'];
const SOURCE_SKELETON_ITEMS = ['first', 'second', 'third', 'fourth'];

function SourceGroupSkeleton() {
  return (
    <div className="space-y-10">
      {SOURCE_SKELETON_GROUPS.map((group) => (
        <section key={group}>
          <div className="mb-4 flex items-center gap-2 px-1">
            <Skeleton className="h-5 w-28 rounded" />
            <Skeleton className="h-4 w-20 rounded" />
          </div>
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {SOURCE_SKELETON_ITEMS.map((item) => (
              <div
                key={`${group}-${item}`}
                className="min-h-45 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] dark:border-border dark:bg-card/35 dark:shadow-none"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <Skeleton className="mb-2 h-5 w-36 rounded" />
                    <Skeleton className="h-5 w-28 rounded-full" />
                  </div>
                  <Skeleton className="h-8 w-24 shrink-0 rounded-full" />
                </div>
                <Skeleton className="mt-5 h-4 w-full max-w-md rounded" />
                <Skeleton className="mt-3 h-4 w-3/4 rounded" />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
export default SourceGroupSkeleton;
