export function ArticleCardSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-4 border-b border-slate-200/70 py-8 last:border-0">
      <div className="flex items-center gap-2">
        <div className="h-3 w-20 rounded bg-slate-100" />
        <div className="h-3 w-24 rounded bg-slate-100" />
      </div>

      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <div className="h-6 w-3/4 rounded bg-slate-100" />
          <div className="space-y-2">
            <div className="h-4 w-full rounded bg-slate-100" />
            <div className="h-4 w-full rounded bg-slate-100" />
            <div className="h-4 w-2/3 rounded bg-slate-100" />
          </div>
          <div className="flex gap-2 mt-2">
            <div className="h-5 w-14 rounded-full bg-slate-100" />
            <div className="h-5 w-16 rounded-full bg-slate-100" />
          </div>
        </div>

        <div className="aspect-[4/3] w-full shrink-0 rounded-md bg-slate-100 md:w-48" />
      </div>
    </div>
  )
}
