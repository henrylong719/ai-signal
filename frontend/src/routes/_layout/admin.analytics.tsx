import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { AlertCircleIcon, ArrowLeft, BarChart3, RefreshCw } from 'lucide-react'
import { DateTime } from 'luxon'
import { useState } from 'react'
import type {
  AdminReadGuestFunnelData,
  CtaLocationRow,
  GuestFunnelResponse,
  TopArticleRow,
  TopSourceRow,
  TopTopicRow,
} from '@/client'
import { AdminService } from '@/client'
import { PageContainer, PageHeader } from '@/components/Layout/Page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'

type DateRange = NonNullable<AdminReadGuestFunnelData['range']>

const RANGE_OPTIONS: Array<{ value: DateRange; label: string }> = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: 'all', label: 'All time' },
]

const DEFAULT_RANGE: DateRange = '30d'

function getGuestFunnelQueryOptions(range: DateRange) {
  return {
    queryFn: () => AdminService.readGuestFunnel({ range }),
    queryKey: ['admin', 'guest-funnel', range] as const,
    // Keep the dashboard reasonably fresh without hammering the DB on
    // every tab focus — funnel data trends over days, not seconds.
    staleTime: 1000 * 60,
  }
}

export const Route = createFileRoute('/_layout/admin/analytics')({
  component: GuestFunnelPage,
  head: () => ({
    meta: [
      {
        title: 'Guest Funnel - Admin',
      },
    ],
  }),
})

function GuestFunnelPage() {
  const [range, setRange] = useState<DateRange>(DEFAULT_RANGE)
  const query = useQuery(getGuestFunnelQueryOptions(range))

  return (
    <PageContainer
      variant="default"
      spacing="compact"
      className="flex flex-col gap-8"
    >
      <PageHeader
        className="mb-0 border-slate-200/70 pb-6"
        eyebrow={
          <Link
            to="/admin"
            className="mb-3 inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 transition-colors hover:text-slate-600 dark:text-muted-foreground dark:hover:text-foreground"
          >
            <ArrowLeft className="size-3" />
            Admin
          </Link>
        }
        eyebrowClassName="mb-3"
        title="Guest funnel"
        titleClassName="tracking-normal"
        description="How logged-out visitors interact with AI Signal before signing up. First-party, anonymous, retained only as aggregate events."
        descriptionClassName="max-w-xl"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={range}
              onValueChange={(value) => setRange(value as DateRange)}
            >
              <SelectTrigger className="h-9 w-[170px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RANGE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
              aria-busy={query.isFetching}
              className="gap-2"
            >
              <RefreshCw
                className={cn('size-3.5', query.isFetching && 'animate-spin')}
              />
              {query.isFetching ? 'Refreshing' : 'Refresh'}
            </Button>
          </div>
        }
      />

      <FunnelBody
        data={query.data}
        isPending={query.isPending}
        isError={query.isError}
        range={range}
      />
    </PageContainer>
  )
}

function FunnelBody({
  data,
  isPending,
  isError,
  range,
}: {
  data: GuestFunnelResponse | undefined
  isPending: boolean
  isError: boolean
  range: DateRange
}) {
  if (isPending) {
    return <FunnelSkeleton />
  }

  if (isError || !data) {
    return (
      <EmptyState
        icon={<AlertCircleIcon className="h-5 w-5 stroke-[1.6]" />}
        title="Could not load guest analytics"
        description="The admin analytics endpoint returned an error. Try refreshing or check the backend logs."
      />
    )
  }

  const totalEvents = Object.values(data.counts).reduce(
    (sum, count) => sum + (count ?? 0),
    0,
  )

  if (totalEvents === 0) {
    return (
      <EmptyState
        icon={<BarChart3 className="h-5 w-5 stroke-[1.6]" />}
        title="No guest analytics yet"
        description="Once logged-out visitors start interacting with AI Signal, funnel data will appear here."
      />
    )
  }

  return (
    <div className="flex flex-col gap-10">
      <SummarySection counts={data.counts} rates={data.rates} />
      <FunnelSection data={data} range={range} />
    </div>
  )
}

function FunnelSection({
  data,
  range,
}: {
  data: GuestFunnelResponse
  range: DateRange
}) {
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <Panel
        title="Top clicked articles"
        description={`Articles guests opened most often in ${labelForRange(range).toLowerCase()}.`}
      >
        <TopArticlesTable rows={data.top_articles ?? []} />
      </Panel>
      <Panel
        title="Top clicked sources"
        description="Sources guests engaged with — both direct clicks and article opens."
      >
        <TopSourcesTable rows={data.top_sources ?? []} />
      </Panel>
      <Panel
        title="Top clicked topics"
        description="Topic chips and category filters logged-out visitors clicked."
      >
        <TopTopicsTable rows={data.top_topics ?? []} />
      </Panel>
      <Panel
        title="Sign-up CTA performance"
        description="Where guests clicked sign-up. Per-location conversion attribution is on the follow-up list."
      >
        <CtaLocationsTable rows={data.signup_cta_locations ?? []} />
      </Panel>
    </div>
  )
}

function SummarySection({
  counts,
  rates,
}: {
  counts: GuestFunnelResponse['counts']
  rates: GuestFunnelResponse['rates']
}) {
  const cards: Array<{ label: string; value: string; hint?: string }> = [
    { label: 'Guest visits', value: formatInt(counts.guest_page_view ?? 0) },
    {
      label: 'Article clicks',
      value: formatInt(counts.guest_article_click ?? 0),
    },
    {
      label: 'Sign-up CTA clicks',
      value: formatInt(counts.guest_signup_click ?? 0),
    },
    {
      label: 'Sign-ups completed',
      value: formatInt(counts.guest_signup_completed ?? 0),
    },
    {
      label: 'Article click rate',
      value: formatPercent(rates.article_click_rate ?? 0),
      hint: 'Clicks ÷ visits',
    },
    {
      label: 'CTA → signup',
      value: formatPercent(rates.signup_conversion_rate ?? 0),
      hint: 'Completed ÷ CTA clicks',
    },
  ]

  return (
    <section
      aria-label="Summary metrics"
      className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6"
    >
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-xl border border-slate-200/70 bg-white px-4 py-4 shadow-[0_1px_1px_rgba(15,23,42,0.025)] dark:border-border dark:bg-card/45 dark:shadow-none"
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-muted-foreground">
            {card.label}
          </p>
          <p className="mt-2 font-display text-2xl font-semibold text-slate-950 dark:text-foreground">
            {card.value}
          </p>
          {card.hint && (
            <p className="mt-1 text-xs text-slate-400 dark:text-muted-foreground/80">
              {card.hint}
            </p>
          )}
        </div>
      ))}
    </section>
  )
}

function Panel({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <section
      aria-label={title}
      className="overflow-hidden rounded-xl border border-slate-200/70 bg-white shadow-[0_1px_1px_rgba(15,23,42,0.025)] dark:border-border dark:bg-card/45 dark:shadow-none"
    >
      <div className="border-b border-slate-200/70 px-5 py-4 dark:border-border">
        <h2 className="font-display text-base font-semibold text-slate-950 dark:text-foreground">
          {title}
        </h2>
        {description && (
          <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      <div className="overflow-x-auto px-2 py-2 sm:px-3 sm:py-3">
        {children}
      </div>
    </section>
  )
}

function TopArticlesTable({ rows }: { rows: TopArticleRow[] }) {
  if (rows.length === 0) {
    return <EmptyRow text="No guest article clicks yet." />
  }
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Article</TableHead>
          <TableHead>Source</TableHead>
          <TableHead className="text-right">Clicks</TableHead>
          <TableHead className="hidden md:table-cell">Published</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.article_id}>
            <TableCell className="font-medium text-slate-900 dark:text-foreground">
              {row.url ? (
                <a
                  href={row.url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-sm hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15"
                >
                  {row.title ?? '(deleted article)'}
                </a>
              ) : (
                (row.title ?? '(deleted article)')
              )}
            </TableCell>
            <TableCell>
              {row.source_name ?? (
                <span className="text-slate-400 dark:text-muted-foreground">
                  —
                </span>
              )}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {row.guest_clicks}
            </TableCell>
            <TableCell className="hidden text-slate-500 md:table-cell dark:text-muted-foreground">
              {row.published_at
                ? DateTime.fromISO(row.published_at).toLocaleString(
                    DateTime.DATE_MED,
                  )
                : '—'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function TopSourcesTable({ rows }: { rows: TopSourceRow[] }) {
  if (rows.length === 0) {
    return <EmptyRow text="No guest source clicks yet." />
  }
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Source</TableHead>
          <TableHead className="text-right">Clicks</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.source_name}>
            <TableCell className="font-medium text-slate-900 dark:text-foreground">
              {row.source_name}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {row.guest_clicks}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function TopTopicsTable({ rows }: { rows: TopTopicRow[] }) {
  if (rows.length === 0) {
    return <EmptyRow text="No guest topic clicks yet." />
  }
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Topic</TableHead>
          <TableHead className="text-right">Clicks</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.topic}>
            <TableCell className="font-medium text-slate-900 dark:text-foreground">
              <Badge variant="secondary" className="font-normal">
                {row.topic}
              </Badge>
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {row.guest_clicks}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function CtaLocationsTable({ rows }: { rows: CtaLocationRow[] }) {
  if (rows.length === 0) {
    return <EmptyRow text="No sign-up CTA clicks yet." />
  }
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Location</TableHead>
          <TableHead className="text-right">Clicks</TableHead>
          <TableHead className="hidden text-right md:table-cell">
            Completed
          </TableHead>
          <TableHead className="hidden text-right md:table-cell">
            Conversion
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.location}>
            <TableCell className="font-medium text-slate-900 dark:text-foreground">
              {row.location}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {row.clicks}
            </TableCell>
            <TableCell className="hidden text-right tabular-nums md:table-cell">
              {row.completed_signups ?? (
                <span className="text-slate-400 dark:text-muted-foreground">
                  —
                </span>
              )}
            </TableCell>
            <TableCell className="hidden text-right tabular-nums md:table-cell">
              {row.conversion_rate != null
                ? formatPercent(row.conversion_rate)
                : '—'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function EmptyRow({ text }: { text: string }) {
  return (
    <p className="px-3 py-6 text-center text-sm text-slate-500 dark:text-muted-foreground">
      {text}
    </p>
  )
}

function EmptyState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div
      role="status"
      className="mx-auto max-w-xl rounded-xl border border-slate-200/70 bg-white px-6 py-10 text-center shadow-[0_1px_2px_rgba(15,23,42,0.03)] dark:border-border dark:bg-card/45 dark:shadow-none"
    >
      <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 text-slate-400 ring-1 ring-slate-200/80 dark:bg-muted dark:text-muted-foreground dark:ring-border">
        {icon}
      </div>
      <h2 className="font-display text-lg font-semibold text-slate-950 dark:text-foreground">
        {title}
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500 dark:text-muted-foreground">
        {description}
      </p>
    </div>
  )
}

function FunnelSkeleton() {
  return (
    <div className="flex flex-col gap-10">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, idx) => (
          // eslint-disable-next-line react/no-array-index-key -- skeleton placeholder
          <Skeleton key={idx} className="h-20 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-8 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, idx) => (
          // eslint-disable-next-line react/no-array-index-key -- skeleton placeholder
          <Skeleton key={idx} className="h-72 rounded-xl" />
        ))}
      </div>
    </div>
  )
}

function formatInt(value: number): string {
  return new Intl.NumberFormat('en-US').format(Math.round(value))
}

function formatPercent(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(value)
}

function labelForRange(range: DateRange): string {
  return (
    RANGE_OPTIONS.find((opt) => opt.value === range)?.label ?? 'this period'
  )
}
