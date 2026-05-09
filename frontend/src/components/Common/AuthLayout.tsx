import { CheckIcon } from 'lucide-react'

import { Appearance } from '@/components/Common/Appearance'
import { Logo } from '@/components/Common/Logo'
import { SupportFooterLinks } from '@/components/Legal/SupportFooterLinks'

const VALUE_PILLARS = [
  'Personalized AI reading feed',
  'Follow trusted sources & researchers',
  'Save articles for later',
  'Discover signal without the noise',
]

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="grid min-h-svh bg-background lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <BrandPanel />
      <FormColumn>{children}</FormColumn>
    </div>
  )
}

function BrandPanel() {
  const year = new Date().getFullYear()
  return (
    <aside className="relative hidden flex-col overflow-hidden border-r border-border/55 bg-muted/45 lg:flex dark:border-border/40 dark:bg-card/55">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 [background:radial-gradient(60%_45%_at_25%_15%,rgba(15,23,42,0.045),transparent_70%),radial-gradient(50%_40%_at_85%_85%,rgba(15,23,42,0.04),transparent_72%)] dark:[background:radial-gradient(60%_45%_at_25%_15%,rgba(255,235,200,0.05),transparent_72%),radial-gradient(50%_40%_at_85%_85%,rgba(255,235,200,0.04),transparent_75%)]"
      />
      <div className="relative flex flex-1 flex-col gap-12 px-10 pt-14 pb-10 xl:gap-14 xl:px-16 xl:pt-20">
        <Logo variant="full" className="text-[1.55rem]" />

        <div className="max-w-[30rem] space-y-5">
          <h2 className="font-serif text-[2rem] leading-[1.1] tracking-tight text-foreground xl:text-[2.35rem]">
            A calmer way to follow what matters in AI.
          </h2>
          <p className="text-[15px] leading-relaxed text-slate-600 dark:text-muted-foreground">
            Track important research, product launches, and industry signals
            from sources you trust — without the noise of a typical feed.
          </p>
        </div>

        <ul className="grid max-w-[30rem] gap-3">
          {VALUE_PILLARS.map((pillar) => (
            <li
              key={pillar}
              className="flex items-center gap-3 text-[14px] text-slate-700 dark:text-foreground/80"
            >
              <span className="inline-flex size-5 shrink-0 items-center justify-center rounded-full border border-border/65 bg-background/70 text-slate-700 dark:border-border/50 dark:bg-card/70 dark:text-foreground/85">
                <CheckIcon className="size-3 stroke-[2.4]" aria-hidden="true" />
              </span>
              {pillar}
            </li>
          ))}
        </ul>
      </div>

      <div className="relative px-10 pb-10 xl:px-16">
        <p className="text-xs text-slate-500 dark:text-muted-foreground/85">
          © {year} AI Signal · Built for thoughtful readers.
        </p>
      </div>
    </aside>
  )
}

function FormColumn({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="flex items-center gap-3 px-5 pt-5 sm:px-8 sm:pt-6">
        <div className="lg:hidden">
          <Logo variant="full" className="text-xl" />
        </div>
        <div className="ml-auto">
          <Appearance />
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-5 py-8 sm:px-8 sm:py-12">
        <div className="w-full max-w-[400px]">
          <div className="rounded-2xl border border-border/65 bg-card p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_24px_56px_-32px_rgba(15,23,42,0.16)] sm:p-8 dark:border-border/45 dark:bg-card/85 dark:shadow-[0_22px_60px_-32px_rgba(0,0,0,0.55)]">
            {children}
          </div>
        </div>
      </main>

      <footer className="flex justify-center px-5 pt-2 pb-8 sm:px-8">
        <SupportFooterLinks variant="inline" />
      </footer>
    </div>
  )
}
