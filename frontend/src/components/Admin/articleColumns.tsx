import type { ColumnDef } from '@tanstack/react-table'
import { EllipsisVertical, ExternalLink } from 'lucide-react'
import { useState } from 'react'

import type { AdminArticlePublic } from '@/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import DeleteArticle from './DeleteArticle'

export const articleColumns: ColumnDef<AdminArticlePublic>[] = [
  {
    accessorKey: 'title',
    header: 'Article',
    cell: ({ row }) => (
      <div className="max-w-[34rem]">
        <div className="line-clamp-2 font-medium">{row.original.title}</div>
        <a
          href={row.original.url}
          target="_blank"
          rel="noreferrer"
          className="mt-1 inline-flex max-w-full items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <span className="truncate">{row.original.url}</span>
          <ExternalLink className="size-3 shrink-0" />
        </a>
      </div>
    ),
  },
  {
    accessorKey: 'source',
    header: 'Source',
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.original.source}</span>
    ),
  },
  {
    accessorKey: 'category',
    header: 'Category',
    cell: ({ row }) => (
      <Badge variant="secondary">{row.original.category}</Badge>
    ),
  },
  {
    accessorKey: 'saved_count',
    header: 'Saved By',
    cell: ({ row }) => (
      <span className="font-medium tabular-nums">
        {row.original.saved_count}
      </span>
    ),
  },
  {
    accessorKey: 'published_at',
    header: 'Published',
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(row.original.published_at)}
      </span>
    ),
  },
  {
    accessorKey: 'fetched_at',
    header: 'Fetched',
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(row.original.fetched_at)}
      </span>
    ),
  },
  {
    id: 'actions',
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <ArticleActions article={row.original} />
      </div>
    ),
  },
]

function ArticleActions({ article }: { article: AdminArticlePublic }) {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DeleteArticle
          id={article.id}
          title={article.title}
          onSuccess={() => setOpen(false)}
        />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return 'N/A'
  }

  const date = new Date(value)
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  })
}
