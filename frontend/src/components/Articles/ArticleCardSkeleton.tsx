export function ArticleCardSkeleton() {
  return (
    <div className="animate-pulse border-b border-slate-100 py-5 last:border-0 sm:py-6">
      <div className="grid gap-4 rounded-md p-3 sm:p-4 md:grid-cols-[minmax(0,1fr)_13rem] md:gap-5 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="min-w-0 space-y-3.5">
          <div className="flex items-center gap-2">
            <div className="h-3 w-24 rounded bg-slate-200" />
            <div className="h-3 w-16 rounded bg-slate-200" />
          </div>
          <div className="h-7 w-4/5 rounded bg-slate-200" />
          <div className="space-y-2">
            <div className="h-4 w-full rounded bg-slate-200" />
            <div className="h-4 w-11/12 rounded bg-slate-200" />
          </div>
          <div className="space-y-2 border-l-2 border-slate-200 pl-3">
            <div className="h-3 w-28 rounded bg-slate-200" />
            <div className="h-4 w-5/6 rounded bg-slate-200" />
          </div>
        </div>

        <div className="order-first aspect-[16/10] rounded-md bg-slate-200 md:order-none" />

        <div className="flex gap-2 md:col-start-1">
          <div className="h-6 w-20 rounded-full bg-slate-200" />
          <div className="h-6 w-16 rounded-full bg-slate-200" />
        </div>
      </div>
    </div>
  )
}
