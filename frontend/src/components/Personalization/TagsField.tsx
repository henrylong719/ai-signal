import { XIcon } from 'lucide-react'
import { useId, useState } from 'react'

import { capitalize, cn } from '@/lib/utils'

const MAX_TAGS = 20
const MAX_TAG_LENGTH = 32
const SUGGESTED_TAGS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'evals', label: 'evals' },
  { value: 'fine-tuning', label: 'fine-tuning' },
  { value: 'agent memory', label: 'agent memory' },
  { value: 'langgraph', label: 'LangGraph' },
]

interface TagsFieldProps {
  value: string[]
  onChange: (next: string[]) => void
}

/**
 * Free-form tag input with chip rendering.
 *
 * Tag input UX: Enter or comma to add; empty + Backspace removes the
 * last chip; trimmed and lowercased on insert to match the server-side
 * normalization. Max length and max count enforced at the input layer
 * to give immediate feedback before the server rejects.
 */
export function TagsField({ value, onChange }: TagsFieldProps) {
  const [tagInput, setTagInput] = useState('')
  const tagsInputId = useId()
  const tagsHintId = useId()

  const commitTagInput = () => {
    const candidate = tagInput.trim().toLowerCase()
    if (!candidate) return
    if (candidate.length > MAX_TAG_LENGTH) return
    if (value.includes(candidate)) {
      setTagInput('')
      return
    }
    if (value.length >= MAX_TAGS) return
    onChange([...value, candidate])
    setTagInput('')
  }

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      commitTagInput()
    } else if (e.key === 'Backspace' && tagInput === '' && value.length > 0) {
      // Empty input + backspace = remove last chip. Mirrors the
      // pattern in most tag-input UIs (Gmail to-field, etc.).
      onChange(value.slice(0, -1))
    }
  }

  const removeTag = (tag: string) => {
    onChange(value.filter((t) => t !== tag))
  }

  const addSuggestedTag = (tag: string) => {
    if (value.includes(tag) || value.length >= MAX_TAGS) return
    onChange([...value, tag])
  }

  const visibleSuggestedTags = SUGGESTED_TAGS.filter(
    (tag) => !value.includes(tag.value),
  )

  return (
    <div>
      <div className="flex min-h-12 flex-wrap items-center gap-2 rounded-lg border border-slate-200/80 bg-white px-3 py-2 shadow-sm shadow-slate-950/[0.02] transition-colors focus-within:border-slate-400 focus-within:ring-2 focus-within:ring-slate-900/10 dark:border-border dark:bg-transparent dark:shadow-none dark:focus-within:border-ring/55 dark:focus-within:ring-ring/15">
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex min-h-8 max-w-full items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm font-medium leading-snug text-slate-700 dark:border-border dark:bg-accent/70 dark:text-foreground/86"
          >
            <span className="break-words">{capitalize(tag)}</span>
            <button
              type="button"
              onClick={() => removeTag(tag)}
              aria-label={`Remove ${tag}`}
              className="rounded-full p-0.5 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 dark:text-muted-foreground dark:hover:bg-muted dark:hover:text-foreground dark:focus-visible:ring-ring"
            >
              <XIcon className="h-3 w-3 stroke-[2]" />
            </button>
          </span>
        ))}
        <input
          id={tagsInputId}
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={handleTagKeyDown}
          onBlur={commitTagInput}
          disabled={value.length >= MAX_TAGS}
          aria-label="Add a specific tag"
          aria-describedby={tagsHintId}
          placeholder={
            value.length >= MAX_TAGS
              ? `Max ${MAX_TAGS} tags`
              : value.length === 0
                ? 'Add a company, tool, paper, or phrase'
                : ''
          }
          maxLength={MAX_TAG_LENGTH}
          className="min-h-8 min-w-[12rem] flex-1 bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none disabled:cursor-not-allowed dark:text-foreground dark:placeholder:text-muted-foreground"
        />
      </div>
      <div
        id={tagsHintId}
        className="mt-2 flex flex-col gap-1 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between dark:text-muted-foreground/75"
      >
        <p>Press Enter or comma to add a tag.</p>
        <p>
          {value.length}/{MAX_TAGS} tags
        </p>
      </div>
      {visibleSuggestedTags.length > 0 && (
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
          <p className="text-xs font-medium text-slate-400 dark:text-muted-foreground/75">
            Try
          </p>
          <div className="flex flex-wrap gap-2">
            {visibleSuggestedTags.map((tag) => (
              <button
                type="button"
                key={tag.value}
                onClick={() => addSuggestedTag(tag.value)}
                disabled={value.length >= MAX_TAGS}
                className={cn(
                  'inline-flex min-h-8 items-center rounded-full border border-slate-200 bg-slate-50/70 px-3 py-1 text-xs font-medium text-slate-600 transition-colors',
                  'hover:border-slate-300 hover:bg-white hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-45',
                  'dark:border-border dark:bg-transparent dark:text-muted-foreground dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background',
                )}
                aria-label={`Add ${tag.label} tag`}
              >
                {tag.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
