export function AuthIntro({
  description,
  title,
}: {
  description: string
  title: string
}) {
  return (
    <div className="mx-auto w-full max-w-[28rem] text-center">
      <h1 className="text-balance font-serif text-2xl leading-[1.05] tracking-normal text-slate-950 sm:text-3xl dark:text-foreground">
        {title}
      </h1>
      <p className="mx-auto mt-2 text-sm leading-snug text-slate-500 dark:text-muted-foreground">
        {description}
      </p>
    </div>
  )
}
