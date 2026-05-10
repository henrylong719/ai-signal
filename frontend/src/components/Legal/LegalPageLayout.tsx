import type { ReactNode } from 'react';
import { PageContainer } from '@/components/Layout/Page';
import { cn } from '@/lib/utils';

interface LegalPageLayoutProps {
  eyebrow?: string;
  title: ReactNode;
  intro?: ReactNode;
  lastUpdated?: string;
  children: ReactNode;
  contentClassName?: string;
}

export function LegalPageLayout({
  eyebrow,
  title,
  intro,
  lastUpdated,
  children,
  contentClassName,
}: LegalPageLayoutProps) {
  return (
    <PageContainer variant="prose" spacing="spacious">
      <header className="mb-10 border-b border-slate-200/80 pb-8 dark:border-border">
        {eyebrow && (
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-muted-foreground">
            {eyebrow}
          </p>
        )}
        <h1 className="font-display text-3xl font-semibold leading-tight text-slate-950 sm:text-4xl dark:text-foreground">
          {title}
        </h1>
        {intro && (
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600 dark:text-muted-foreground">
            {intro}
          </p>
        )}
      </header>
      <div
        className={cn(
          'space-y-10 text-[0.95rem] leading-7 text-slate-700 dark:text-foreground/86',
          contentClassName,
        )}
      >
        {children}
      </div>
    </PageContainer>
  );
}

interface PolicySectionProps {
  title: ReactNode;
  children: ReactNode;
  id?: string;
}

export function PolicySection({ title, children, id }: PolicySectionProps) {
  return (
    <section id={id} className="space-y-3">
      <h2 className="font-display text-xl font-semibold text-slate-950 sm:text-2xl dark:text-foreground">
        {title}
      </h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

interface PolicyListProps {
  items: ReactNode[];
}

export function PolicyList({ items }: PolicyListProps) {
  return (
    <ul className="ml-5 list-disc space-y-2 marker:text-slate-400 dark:marker:text-muted-foreground">
      {items.map((item, index) => (
        <li key={index} className="pl-1">
          {item}
        </li>
      ))}
    </ul>
  );
}
