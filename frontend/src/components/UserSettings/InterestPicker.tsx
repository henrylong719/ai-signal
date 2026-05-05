import { CheckIcon, XIcon } from "lucide-react"
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
      <div className="max-w-2xl text-sm text-slate-500">
        Could not load your interests. Refresh the page to try again.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <p className="max-w-2xl text-sm leading-6 text-slate-500">
        Pick categories and add specific topics to personalize your For You
        feed.
      </p>

      <div className="grid gap-7 lg:grid-cols-[minmax(0,1.08fr)_minmax(20rem,0.92fr)]">
        <section className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-950">
            Topic Preferences
          </h3>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Choose the broad areas you want to see more often.
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
                    "inline-flex min-h-9 items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-all",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2",
                    selected
                      ? "border-slate-950 bg-slate-950 text-white shadow-sm hover:bg-slate-800"
                      : "border-slate-200 bg-slate-50/80 text-slate-600 hover:border-slate-300 hover:bg-white hover:text-slate-950",
                  )}
                >
                  <CheckIcon
                    className={cn(
                      "h-3.5 w-3.5 transition-opacity",
                      selected ? "opacity-100" : "opacity-0",
                    )}
                  />
                  {cat.label}
                </button>
              )
            })}
          </div>
        </section>

        <section className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-950">
            Specific Tags
          </h3>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Add topics, companies, or technologies. Press Enter to add.
          </p>
          <div className="mt-4 flex min-h-11 flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white p-2 shadow-sm shadow-slate-950/[0.02] transition-colors focus-within:border-slate-400 focus-within:ring-2 focus-within:ring-slate-900/10">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex min-h-7 items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-sm font-medium text-slate-700"
              >
                {capitalize(tag)}
                <button
                  type="button"
                  onClick={() => removeTag(tag)}
                  aria-label={`Remove ${tag}`}
                  className="rounded-full p-0.5 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
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
              className="min-h-7 min-w-[9rem] flex-1 bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none disabled:cursor-not-allowed"
            />
          </div>
          <p className="mt-2 text-xs text-slate-400">
            {tags.length}/{MAX_TAGS} tags
          </p>
        </section>
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-slate-400">
          Preferences update your personalized feed after saving.
        </p>
        <LoadingButton
          onClick={handleSave}
          loading={isSaving}
          disabled={!isDirty || isSaving}
          size="sm"
          className="h-9 w-full bg-slate-950 px-4 font-medium text-white shadow-sm hover:bg-slate-800 sm:w-auto"
        >
          <CheckIcon className="h-4 w-4" />
          Save preferences
        </LoadingButton>
      </div>
    </div>
  )
}

function InterestPickerSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-5 w-full max-w-xl" />
      <div className="grid gap-7 lg:grid-cols-[minmax(0,1.08fr)_minmax(20rem,0.92fr)]">
        <section>
          <Skeleton className="h-6 w-24" />
          <Skeleton className="mt-2 h-4 w-80" />
          <div className="mt-4 flex flex-wrap gap-2">
            {CATEGORIES.map((category) => (
              <Skeleton
                key={category.value}
                className="h-9 w-24 rounded-full"
              />
            ))}
          </div>
        </section>
        <section>
          <Skeleton className="h-6 w-28" />
          <Skeleton className="mt-2 h-4 w-72" />
          <Skeleton className="mt-4 h-12 w-full rounded-md" />
        </section>
      </div>
      <div className="border-t border-slate-100 pt-5">
        <Skeleton className="h-6 w-24" />
      </div>
    </div>
  )
}
