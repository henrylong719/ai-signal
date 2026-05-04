import { createFileRoute, Link } from "@tanstack/react-router"
import { AlertCircleIcon, LogInIcon } from "lucide-react"

import { ArticleListState } from "@/components/Articles/ArticleList"
import ChangePassword from "@/components/UserSettings/ChangePassword"
import DeleteAccount from "@/components/UserSettings/DeleteAccount"
import UserInformation from "@/components/UserSettings/UserInformation"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"

const tabsConfig = [
  { value: "my-profile", title: "My profile", component: UserInformation },
  { value: "password", title: "Password", component: ChangePassword },
  { value: "danger-zone", title: "Danger zone", component: DeleteAccount },
]

export const Route = createFileRoute("/_layout/settings")({
  component: UserSettings,
  head: () => ({
    meta: [
      {
        title: "Settings",
      },
    ],
  }),
})

function SettingsSkeleton() {
  return (
    <div className="px-4 sm:px-6 lg:px-8 flex flex-col gap-6">
      <header className="pt-12 pb-5 border-b border-slate-100">
        <Skeleton className="h-10 w-56 rounded" />
        <Skeleton className="mt-3 h-5 w-full max-w-md rounded" />
      </header>
      <div className="space-y-6">
        <Skeleton className="h-9 w-80 max-w-full rounded-lg" />
        <div className="max-w-md space-y-4">
          <Skeleton className="h-5 w-40 rounded" />
          <Skeleton className="h-9 w-full rounded-md" />
          <Skeleton className="h-9 w-full rounded-md" />
          <Skeleton className="h-9 w-20 rounded-md" />
        </div>
      </div>
    </div>
  )
}

function UserSettings() {
  const { user: currentUser, isLoading, isError } = useAuth()
  const finalTabs = currentUser?.is_superuser
    ? tabsConfig.slice(0, 3)
    : tabsConfig

  if (isLoading) {
    return <SettingsSkeleton />
  }

  if (isError) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 flex flex-col gap-6">
        <ArticleListState
          title="Could not load settings"
          description="Please refresh the page or try again in a moment."
          icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.5]" />}
        />
      </div>
    )
  }

  if (!currentUser) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 flex flex-col gap-6">
        <ArticleListState
          title="Sign in to manage settings"
          description="Account settings are available after you sign in."
          icon={<LogInIcon className="h-5 w-5 stroke-[1.5]" />}
          action={
            <Link
              to="/login"
              className="inline-flex h-9 items-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
            >
              Sign in
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 flex flex-col gap-6">
      <header className="pt-12 pb-5 border-b border-slate-100">
        <h1 className="font-serif text-3xl sm:text-4xl font-medium text-slate-900 tracking-tight">
          User settings
        </h1>
        <p className="mt-3 text-lg text-slate-500 leading-relaxed font-serif">
          Manage your account settings and preferences.
        </p>
      </header>

      <Tabs defaultValue="my-profile">
        <div className="-mx-4 overflow-x-auto px-4 sm:-mx-6 sm:px-6 lg:mx-0 lg:px-0">
          <TabsList className="w-max">
            {finalTabs.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.title}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        {finalTabs.map((tab) => (
          <TabsContent key={tab.value} value={tab.value} className="pt-2">
            <tab.component />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
