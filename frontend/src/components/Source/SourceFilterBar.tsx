import {
  SOURCE_FILTER_LABELS,
  SOURCE_TYPES,
  type source_types,
} from '@/lib/constants'
import { cn } from '@/lib/utils'

interface SourceFilterBarProps {
  selected: source_types
  onSelect: (type: source_types) => void
  types?: source_types[]
}

function SourceFilterBar({
  selected,
  onSelect,
  types = SOURCE_TYPES,
}: SourceFilterBarProps) {
  return (
    <div className="sticky top-16 z-40 -mx-4 mb-6 overflow-x-auto border-y border-slate-200/80 bg-white/95 px-4 py-2.5 backdrop-blur sm:top-18 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8 dark:border-border dark:bg-background/92 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <fieldset className="flex w-max min-w-full gap-2">
        <legend className="sr-only">Filter sources by type</legend>
        {types.map((type) => (
          <button
            type="button"
            key={type}
            onClick={() => onSelect(type)}
            aria-pressed={selected === type}
            className={cn(
              'h-9 shrink-0 rounded-full border px-3.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
              selected === type
                ? 'border-slate-950 bg-slate-950 text-white shadow-sm dark:border-primary dark:bg-primary dark:text-primary-foreground'
                : 'border-slate-200/90 bg-white/90 text-slate-600 shadow-sm shadow-slate-950/2 hover:border-slate-300 hover:bg-white hover:text-slate-950 dark:border-border dark:bg-transparent dark:text-muted-foreground dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent/70 dark:hover:text-foreground',
            )}
          >
            {SOURCE_FILTER_LABELS[type]}
          </button>
        ))}
      </fieldset>
    </div>
  )
}

export default SourceFilterBar
