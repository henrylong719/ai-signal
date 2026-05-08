import { cn } from '@/lib/utils'
import { PageContainer } from '../Layout/Page'
import { Skeleton } from '../ui/skeleton'

function SettingsSkeleton() {
  return (
    <PageContainer variant="narrow" spacing="compact">
      <header className="mb-6 border-b border-slate-200/70 pb-6 dark:border-border">
        <div className="max-w-2xl">
          <Skeleton className="h-4 w-28 rounded" />
          <Skeleton className="mt-4 h-10 w-72 max-w-full rounded" />
          <Skeleton className="mt-3 h-5 w-full max-w-lg rounded" />
        </div>
      </header>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.86fr)]">
        {[0, 1, 2].map((item) => (
          <Skeleton
            key={item}
            className={cn(
              'h-72 rounded-lg',
              item === 2 && 'lg:col-span-2 h-80',
            )}
          />
        ))}
      </div>
    </PageContainer>
  )
}

export default SettingsSkeleton
