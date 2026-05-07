export function AuthIntro({
  description,
  title,
}: {
  description: string
  title: string
}) {
  return (
    <div className="w-full text-center">
      <h1 className="font-serif text-2xl leading-[1.05] tracking-normal text-slate-950 sm:text-3xl dark:text-foreground">
        {title}
      </h1>
      <p className="mx-auto mt-2 text-sm leading-snug text-slate-500 dark:text-muted-foreground">
        {description}
      </p>
    </div>
  )
}
