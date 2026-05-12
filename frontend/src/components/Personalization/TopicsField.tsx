import { CheckIcon } from 'lucide-react'

import type { category as Category } from '@/client'
import { cn } from '@/lib/utils'

// Source of truth for category options. Mirrors the backend Category
// Literal — any addition here must be matched server-side.
const CATEGORIES: { value: Category; label: string }[] = [
  { value: 'agents', label: 'Agents' },
  { value: 'rag', label: 'RAG' },
  { value: 'models', label: 'Models' },
  { value: 'infrastructure', label: 'Infrastructure' },
  { value: 'engineering', label: 'Engineering' },
  { value: 'research', label: 'Research' },
  { value: 'applications', label: 'Applications' },
  { value: 'business', label: 'Business' },
  { value: 'policy', label: 'Policy' },
  { value: 'safety', label: 'Safety' },
  { value: 'education', label: 'Education' },
  { value: 'other', label: 'Other' },
]

interface TopicsFieldProps {
  value: Category[]
  onChange: (next: Category[]) => void
}

/**
 * Multi-select chip picker for topic categories.
 *
 * Stateless / controlled — the parent owns the form state and dirty-tracking.
 * Toggle-on-click semantics with larger chips because topics are the primary
 * taste signal on the personalization page.
 */
export function TopicsField({ value, onChange }: TopicsFieldProps) {
  const toggle = (cat: Category) => {
    onChange(
      value.includes(cat) ? value.filter((c) => c !== cat) : [...value, cat],
    )
  }

  return (
    <div className="flex flex-wrap gap-2.5">
      {CATEGORIES.map((cat) => {
        const selected = value.includes(cat.value)
        return (
          <button
            type="button"
            key={cat.value}
            onClick={() => toggle(cat.value)}
            aria-pressed={selected}
            className={cn(
              'inline-flex min-h-11 items-center gap-2 rounded-full border px-4 py-2 text-[15px] font-medium leading-none transition-all',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
              selected
                ? 'border-slate-950 bg-slate-950 text-white shadow-sm shadow-slate-950/10 hover:bg-slate-800 dark:border-primary dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/88'
                : 'border-slate-200 bg-white text-slate-600 shadow-sm shadow-slate-950/[0.02] hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground',
            )}
          >
            <span
              className={cn(
                'flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-colors',
                selected
                  ? 'border-white/45 bg-white/10 dark:border-primary-foreground/45 dark:bg-primary-foreground/10'
                  : 'border-slate-300 bg-white text-transparent dark:border-border dark:bg-background/20',
              )}
              aria-hidden="true"
            >
              <CheckIcon
                className={cn(
                  'h-3 w-3 transition-opacity',
                  selected ? 'opacity-100' : 'opacity-0',
                )}
              />
            </span>
            {cat.label}
          </button>
        )
      })}
    </div>
  )
}
