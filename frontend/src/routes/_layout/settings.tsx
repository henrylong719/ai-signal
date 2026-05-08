import { createFileRoute, Link } from '@tanstack/react-router';
import {
  AlertCircleIcon,
  LinkIcon,
  LogInIcon,
  ShieldCheckIcon,
  Trash2Icon,
  UserRoundIcon,
} from 'lucide-react';
import type { ReactNode } from 'react';

import { ArticleListState } from '@/components/Articles/ArticleList';
import AuthModal from '@/components/Auth/AuthModal';
import { PageContainer, PageHeader } from '@/components/Layout/Page';
import ChangePassword from '@/components/UserSettings/ChangePassword';
import ConnectedAccounts from '@/components/UserSettings/ConnectedAccounts';
import DeleteAccount from '@/components/UserSettings/DeleteAccount';
import UserInformation from '@/components/UserSettings/UserInformation';
import { Skeleton } from '@/components/ui/skeleton';
import useAuth from '@/hooks/useAuth';
import { cn } from '@/lib/utils';

export const Route = createFileRoute('/_layout/settings')({
  component: UserSettings,
  head: () => ({
    meta: [
      {
        title: 'Settings',
      },
    ],
  }),
});

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
  );
}

function UserSettings() {
  const { user: currentUser, isLoading, isError } = useAuth();

  if (isLoading) {
    return <SettingsSkeleton />;
  }

  if (isError) {
    return (
      <PageContainer
        variant="narrow"
        spacing="compact"
        className="flex flex-col gap-6"
      >
        <ArticleListState
          title="Could not load settings"
          description="Please refresh the page or try again in a moment."
          icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
        />
      </PageContainer>
    );
  }

  if (!currentUser) {
    return (
      <PageContainer
        variant="narrow"
        spacing="compact"
        className="flex flex-col gap-6"
      >
        <ArticleListState
          title="Sign in to manage settings"
          description="Account settings are available after you sign in."
          icon={<LogInIcon className="h-5 w-5 stroke-[1.5]" />}
          action={
            <AuthModal
              title="Sign in to manage settings"
              description="Access your profile, sign-in methods, and account security settings."
              trigger={
                <button
                  type="button"
                  className="inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/88 dark:focus-visible:ring-ring dark:focus-visible:ring-offset-background"
                >
                  Sign in
                </button>
              }
            />
          }
        />
      </PageContainer>
    );
  }

  const hasPassword = currentUser.has_password ?? true;

  return (
    <PageContainer spacing="compact">
      <PageHeader
        className="mb-6 border-slate-200/70 pb-6"
        eyebrow="Account"
        eyebrowClassName="tracking-[0.18em] text-slate-400"
        title="Account Settings"
        titleClassName="tracking-normal"
        description={
          <>
            Manage your identity and security. To shape your personalized feed,
            head to{' '}
            <Link
              to="/personalization"
              className="font-medium text-slate-700 underline decoration-slate-300 underline-offset-4 transition-colors hover:text-slate-950 hover:decoration-slate-500 dark:text-foreground/86 dark:decoration-border dark:hover:text-foreground dark:hover:decoration-foreground/40"
            >
              Tune your signal
            </Link>
            .
          </>
        }
        descriptionClassName="max-w-xl"
        actions={
          <div className="inline-flex max-w-full items-center gap-2 self-start rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-500 shadow-sm md:self-auto dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none">
            <span className="h-2 w-2 rounded-full bg-emerald-500/85" />
            <span className="truncate">{currentUser.email}</span>
          </div>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.86fr)]">
        <SettingsSection
          title="Profile Information"
          description="Update the personal details attached to your account."
          icon={<UserRoundIcon className="h-4 w-4 stroke-[1.8]" />}
        >
          <UserInformation />
        </SettingsSection>

        {hasPassword && (
          <SettingsSection
            title="Password & Security"
            description="Keep your sign-in credentials current and protected."
            icon={<ShieldCheckIcon className="h-4 w-4 stroke-[1.8]" />}
          >
            <ChangePassword />
          </SettingsSection>
        )}

        <SettingsSection
          title="Sign-in Methods"
          description="Review the ways you can access this account."
          icon={<LinkIcon className="h-4 w-4 stroke-[1.8]" />}
          className={hasPassword ? 'lg:col-span-2' : 'lg:self-start'}
        >
          <ConnectedAccounts hasPassword={hasPassword} />
        </SettingsSection>

        <SettingsSection
          title="Danger Zone"
          description="Permanent account actions live here."
          icon={<Trash2Icon className="h-4 w-4 stroke-[1.8]" />}
          danger
          className="lg:col-span-2"
        >
          <DeleteAccount />
        </SettingsSection>
      </div>
    </PageContainer>
  );
}

function SettingsSection({
  title,
  description,
  icon,
  danger = false,
  children,
  className,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  danger?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        'overflow-hidden rounded-lg border bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_32px_rgba(15,23,42,0.04)] dark:bg-card/35 dark:shadow-none',
        danger
          ? 'border-red-200/80 dark:border-red-400/20'
          : 'border-slate-200/80 dark:border-border',
        className,
      )}
    >
      <div
        className={cn(
          'flex gap-4 border-b px-5 py-4 sm:px-6',
          danger
            ? 'border-red-100 bg-red-50/60 dark:border-red-400/15 dark:bg-transparent'
            : 'border-slate-100 bg-slate-50/70 dark:border-border dark:bg-transparent',
        )}
      >
        <div
          className={cn(
            'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border',
            danger
              ? 'border-red-200 bg-white text-red-600 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-300'
              : 'border-slate-200 bg-white text-slate-600 dark:border-border dark:bg-muted/35 dark:text-muted-foreground',
          )}
        >
          {icon}
        </div>
        <div className="min-w-0">
          <h2
            className={cn(
              'text-base font-semibold tracking-tight',
              danger
                ? 'text-red-950 dark:text-red-100'
                : 'text-slate-950 dark:text-foreground',
            )}
          >
            {title}
          </h2>
          <p
            className={cn(
              'mt-1 text-sm leading-6',
              danger
                ? 'text-red-700/75 dark:text-red-200/70'
                : 'text-slate-500 dark:text-muted-foreground',
            )}
          >
            {description}
          </p>
        </div>
      </div>
      <div className="p-5 sm:p-6">{children}</div>
    </section>
  );
}
