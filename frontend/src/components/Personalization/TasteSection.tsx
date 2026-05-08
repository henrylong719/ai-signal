import { ReactNode } from 'react';

function TasteSection({
  eyebrow,
  title,
  description,
  count,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  count: string;
  children: ReactNode;
}) {
  return (
    <section className="py-8 sm:py-10">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-xl">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400 dark:text-muted-foreground">
            {eyebrow}
          </p>
          <h2 className="font-display text-2xl font-semibold tracking-normal text-slate-950 dark:text-foreground">
            {title}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
            {description}
          </p>
        </div>
        <span className="inline-flex min-h-8 w-fit items-center rounded-full border border-slate-200 bg-white px-3 text-xs font-medium text-slate-500 shadow-sm shadow-slate-950/[0.02] dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none">
          {count}
        </span>
      </div>
      {children}
    </section>
  );
}

export default TasteSection;
