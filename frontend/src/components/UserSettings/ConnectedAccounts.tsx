import { useQuery } from '@tanstack/react-query'
import {
  CheckCircle2Icon,
  KeyRoundIcon,
  LinkIcon,
  MailIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { FaFacebook, FaGithub } from 'react-icons/fa'
import { FcGoogle } from 'react-icons/fc'

import { type OAuthAccountPublic, UsersService } from '@/client'

const providerMeta: Record<
  string,
  {
    icon: ReactNode
    label: string
  }
> = {
  github: {
    icon: <FaGithub className="size-5 text-[#24292f]" />,
    label: 'GitHub',
  },
  google: {
    icon: <FcGoogle className="size-5" />,
    label: 'Google',
  },
  facebook: {
    icon: <FaFacebook className="size-5 text-[#1877f2]" />,
    label: 'Facebook',
  },
}

function providerLabel(provider: string) {
  return providerMeta[provider]?.label ?? provider
}

function providerIcon(provider: string) {
  return (
    providerMeta[provider]?.icon ?? (
      <LinkIcon className="size-5 stroke-[1.8] text-slate-500 dark:text-muted-foreground" />
    )
  )
}

function ConnectedAccountRow({ account }: { account: OAuthAccountPublic }) {
  return (
    <li className="flex min-w-0 items-start gap-3 border-b border-slate-100 py-4 last:border-0 dark:border-border">
      <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white dark:border-border dark:bg-muted/35">
        {providerIcon(account.provider)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <h3 className="text-sm font-semibold text-slate-950 dark:text-foreground">
            {providerLabel(account.provider)}
          </h3>
          {account.email_verified && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-300">
              <CheckCircle2Icon className="size-3.5" />
              Verified
            </span>
          )}
        </div>
        <div className="mt-1 flex min-w-0 items-center gap-1.5 text-sm text-slate-500 dark:text-muted-foreground">
          <MailIcon className="size-3.5 shrink-0" />
          <span className="truncate">{account.email}</span>
        </div>
        {account.display_name && (
          <p className="mt-1 truncate text-sm text-slate-400 dark:text-muted-foreground/75">
            Connected as {account.display_name}
          </p>
        )}
      </div>
      {account.avatar_url && (
        <img
          src={account.avatar_url}
          alt=""
          className="h-9 w-9 shrink-0 rounded-full bg-slate-100 object-cover dark:bg-muted"
        />
      )}
    </li>
  )
}

function PasswordMethodRow({ hasPassword }: { hasPassword: boolean }) {
  return (
    <li className="flex min-w-0 items-start gap-3 border-b border-slate-100 py-4 last:border-0 dark:border-border">
      <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white dark:border-border dark:bg-muted/35">
        <KeyRoundIcon className="size-5 stroke-[1.8] text-slate-500 dark:text-muted-foreground" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <h3 className="text-sm font-semibold text-slate-950 dark:text-foreground">
            Password
          </h3>
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-muted/60 dark:text-muted-foreground">
            {hasPassword ? 'Enabled' : 'Not enabled'}
          </span>
        </div>
        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-muted-foreground">
          {hasPassword
            ? 'You can sign in with your email address and password.'
            : 'You can keep signing in with your connected social accounts.'}
        </p>
      </div>
    </li>
  )
}

export default function ConnectedAccounts({
  hasPassword,
}: {
  hasPassword: boolean
}) {
  const { data, isError, isLoading } = useQuery({
    queryFn: () => UsersService.readUserOauthAccounts(),
    queryKey: ['oauthAccounts'],
  })

  if (isLoading) {
    return (
      <p className="text-sm text-slate-500 dark:text-muted-foreground">
        Loading connected accounts...
      </p>
    )
  }

  if (isError) {
    return (
      <p className="text-sm text-slate-500 dark:text-muted-foreground">
        Could not load connected accounts. Refresh the page to try again.
      </p>
    )
  }

  return (
    <div className="">
      <ul className="mt-3 divide-y-0">
        <PasswordMethodRow hasPassword={hasPassword} />
        {data?.data.map((account) => (
          <ConnectedAccountRow
            account={account}
            key={`${account.provider}:${account.email}`}
          />
        ))}
      </ul>
      {!data?.data.length && (
        <p className="mt-2 text-sm text-slate-500 dark:text-muted-foreground">
          No social sign-in providers are connected to this account.
        </p>
      )}
    </div>
  )
}
