function DigestState({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="rounded-lg border border-slate-200/80 bg-white px-6 py-10 text-center dark:border-border dark:bg-card/35">
      <h2 className="font-serif text-2xl font-medium text-slate-950 dark:text-foreground">
        {title}
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500 dark:text-muted-foreground">
        {description}
      </p>
    </div>
  )
}

export default DigestState
