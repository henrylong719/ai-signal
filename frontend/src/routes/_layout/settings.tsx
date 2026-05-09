import { createFileRoute, Link } from '@tanstack/react-router'
import {
  AlertCircleIcon,
  LinkIcon,
  LogInIcon,
  ShieldCheckIcon,
  Trash2Icon,
  UserRoundIcon,
} from 'lucide-react'

import { ArticleListState } from '@/components/Articles/ArticleList'
import AuthModal from '@/components/Auth/AuthModal'
import { PageContainer, PageHeader } from '@/components/Layout/Page'
import SettingsSection from '@/components/Setting/SettingsSection'
import SettingsSkeleton from '@/components/Setting/SettingsSkeleton'
import ChangePassword from '@/components/UserSettings/ChangePassword'
import ConnectedAccounts from '@/components/UserSettings/ConnectedAccounts'
import DeleteAccount from '@/components/UserSettings/DeleteAccount'
import UserInformation from '@/components/UserSettings/UserInformation'
import useAuth from '@/hooks/useAuth'

export const Route = createFileRoute('/_layout/settings')({
  component: UserSettings,
  head: () => ({
    meta: [
      {
        title: 'Settings',
      },
    ],
  }),
})

function UserSettings() {
  const { user: currentUser, isLoading, isError } = useAuth()

  if (isLoading) {
    return <SettingsSkeleton />
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
    )
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
                  className="inline-flex h-9 items-center rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-foreground dark:text-background dark:hover:bg-foreground/92 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Sign in
                </button>
              }
            />
          }
        />
      </PageContainer>
    )
  }

  const hasPassword = currentUser.has_password ?? true

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
  )
}
