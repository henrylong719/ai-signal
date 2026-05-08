import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import { cn } from '@/lib/utils';

export const pageContainerWidths = {
  shell: 'max-w-[1265px]',
  wide: 'max-w-[1200px]',
  default: 'max-w-6xl',
  narrow: 'max-w-5xl',
} as const;

export const pageContainerGutters = 'px-4 sm:px-6 lg:px-8';

const pageContainerSpacing = {
  none: '',
  compact: 'pb-16 pt-8 sm:pb-20 sm:pt-10',
  spacious: 'pb-16 pt-10 sm:pb-20 sm:pt-12',
} as const;

type PageContainerVariant = keyof typeof pageContainerWidths;
type PageContainerSpacing = keyof typeof pageContainerSpacing;

interface PageContainerProps extends ComponentPropsWithoutRef<'div'> {
  variant?: PageContainerVariant;
  spacing?: PageContainerSpacing;
  gutters?: boolean;
}

export function PageContainer({
  variant = 'default',
  spacing = 'spacious',
  gutters = false,
  className,
  ...props
}: PageContainerProps) {
  return (
    <div
      className={cn(
        'mx-auto w-full',
        gutters && pageContainerGutters,
        pageContainerWidths[variant],
        pageContainerSpacing[spacing],
        className,
      )}
      {...props}
    />
  );
}

interface PageHeaderProps extends Omit<
  ComponentPropsWithoutRef<'header'>,
  'title'
> {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  contentClassName?: string;
  eyebrowClassName?: string;
  titleClassName?: string;
  descriptionClassName?: string;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  children,
  className,
  contentClassName,
  eyebrowClassName,
  titleClassName,
  descriptionClassName,
  ...props
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        'mb-7 flex flex-col gap-5 border-b border-slate-200/80 pb-7 md:flex-row md:items-end md:justify-between dark:border-border',
        className,
      )}
      {...props}
    >
      <div className={cn('', contentClassName)}>
        {eyebrow && (
          <p
            className={cn(
              'mb-3 text-xs font-semibold uppercase text-slate-500 dark:text-muted-foreground',
              eyebrowClassName,
            )}
          >
            {eyebrow}
          </p>
        )}
        <h1
          className={cn(
            'font-display text-3xl font-semibold text-slate-950 sm:text-4xl dark:text-foreground',
            titleClassName,
          )}
        >
          {title}
        </h1>
        {description && (
          <p
            className={cn(
              'mt-3 text-base leading-7 text-slate-500 dark:text-muted-foreground',
              descriptionClassName,
            )}
          >
            {description}
          </p>
        )}
        {children}
      </div>
      {actions}
    </header>
  );
}
