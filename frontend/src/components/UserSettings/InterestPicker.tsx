import { XIcon } from "lucide-react"
import { useEffect, useId, useMemo, useState } from "react"

import type { category as Category } from "@/client"
import { LoadingButton } from "@/components/ui/loading-button"
import { Skeleton } from "@/components/ui/skeleton"
import { useInterests } from "@/hooks/useInterests"
import { capitalize, cn } from "@/lib/utils"

// Source of truth for category options. Mirrors the backend Category
// Literal — any addition here must be matched server-side.
const CATEGORIES: { value: Category; label: string }[] = [
  { value: "agents", label: "Agents" },
  { value: "rag", label: "RAG" },
  { value: "models", label: "Models" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "engineering", label: "Engineering" },
  { value: "research", label: "Research" },
  { value: "applications", label: "Applications" },
  { value: "business", label: "Business" },
  { value: "policy", label: "Policy" },
  { value: "safety", label: "Safety" },
  { value: "other", label: "Other" },
]

const MAX_TAGS = 20
const MAX_TAG_LENGTH = 32

/** Settings tab content for managing the user's recommendation interests. */
export default function InterestPicker() {
  const { interests, isLoading, isError, save, isSaving } = useInterests()

  // Working copy of the form. Initialised from the server value, then
  // mutated locally as the user clicks. We compare against the server
  // value to compute the dirty flag.
  const [categories, setCategories] = useState<Category[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState("")
  const tagsInputId = useId()

  // Sync local state whenever the server value loads or changes (after a save).
  // Without this, a successful save would leave the form looking dirty until
  // the user navigates away and back.
  useEffect(() => {
    if (interests) {
      setCategories(interests.categories ?? [])
      setTags(interests.tags ?? [])
    }
  }, [interests])

  const isDirty = useMemo(() => {
    if (!interests) return categories.length > 0 || tags.length > 0
    const savedCategories = interests.categories ?? []
    const savedTags = interests.tags ?? []
    const sameCategories =
      categories.length === savedCategories.length &&
      categories.every((c) => savedCategories.includes(c))
    const sameTags =
      tags.length === savedTags.length &&
      tags.every((t) => savedTags.includes(t))
    return !(sameCategories && sameTags)
  }, [categories, tags, interests])

  const toggleCategory = (cat: Category) => {
    setCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat],
    )
  }

  // Tag input UX: Enter or comma to add; empty + Backspace removes the
  // last chip; trimmed and lowercased on insert to match the server-side
  // normalization.
  const commitTagInput = () => {
    const candidate = tagInput.trim().toLowerCase()
    if (!candidate) return
    if (candidate.length > MAX_TAG_LENGTH) return
    if (tags.includes(candidate)) {
      setTagInput("")
      return
    }
    if (tags.length >= MAX_TAGS) return
    setTags((prev) => [...prev, candidate])
    setTagInput("")
  }

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      commitTagInput()
    } else if (e.key === "Backspace" && tagInput === "" && tags.length > 0) {
      // Empty input + backspace = remove last chip. Mirrors the
      // pattern in most tag-input UIs (Gmail to-field, etc.).
      setTags((prev) => prev.slice(0, -1))
    }
  }

  const removeTag = (tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag))
  }

  const handleSave = () => {
    save({ categories, tags })
  }

  if (isLoading) {
    return <InterestPickerSkeleton />
  }

  if (isError) {
    return (
      <div className="max-w-2xl pt-6 text-sm text-slate-500">
        Could not load your interests. Refresh the page to try again.
      </div>
    )
  }

  return (
    <div className="max-w-2xl pt-6 flex flex-col gap-8">
      <section>
        <h2 className="font-serif text-xl font-medium text-slate-900">
          Topics
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Pick the categories you want to see more of in your For You feed.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {CATEGORIES.map((cat) => {
            const selected = categories.includes(cat.value)
            return (
              <button
                type="button"
                key={cat.value}
                onClick={() => toggleCategory(cat.value)}
                aria-pressed={selected}
                className={cn(
                  "rounded-full border px-3 py-1 text-sm font-sans transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2",
                  selected
                    ? "border-slate-900 bg-slate-900 text-white hover:bg-slate-700"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50",
                )}
              >
                {cat.label}
              </button>
            )
          })}
        </div>
      </section>

      <section>
        <h2 className="font-serif text-xl font-medium text-slate-900">Tags</h2>
        <p className="mt-1 text-sm text-slate-500">
          Add specific topics or technologies. Press Enter to add.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white p-2 focus-within:border-slate-300">
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-sm text-slate-700"
            >
              {capitalize(tag)}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                aria-label={`Remove ${tag}`}
                className="rounded-full p-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700"
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
            disabled={tags.length >= MAX_TAGS}
            placeholder={
              tags.length >= MAX_TAGS
                ? `Max ${MAX_TAGS} tags`
                : tags.length === 0
                  ? "e.g. evals, fine-tuning"
                  : ""
            }
            maxLength={MAX_TAG_LENGTH}
            className="min-w-[8rem] flex-1 bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none disabled:cursor-not-allowed"
          />
        </div>
        <p className="mt-1.5 text-xs text-slate-400">
          {tags.length}/{MAX_TAGS} tags
        </p>
      </section>

      <div>
        <LoadingButton
          onClick={handleSave}
          loading={isSaving}
          disabled={!isDirty || isSaving}
        >
          Save interests
        </LoadingButton>
      </div>
    </div>
  )
}

function InterestPickerSkeleton() {
  return (
    <div className="max-w-2xl pt-6 flex flex-col gap-8">
      <section>
        <Skeleton className="h-6 w-24" />
        <Skeleton className="mt-2 h-4 w-80" />
        <div className="mt-4 flex flex-wrap gap-2">
          {CATEGORIES.map((category) => (
            <Skeleton key={category.value} className="h-7 w-20 rounded-full" />
          ))}
        </div>
      </section>
      <section>
        <Skeleton className="h-6 w-16" />
        <Skeleton className="mt-2 h-4 w-72" />
        <Skeleton className="mt-4 h-12 w-full rounded-md" />
      </section>
    </div>
  )
}
