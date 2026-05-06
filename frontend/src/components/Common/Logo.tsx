import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content =
    variant === "responsive" ? (
      <span
        className={cn(
          "inline-flex items-center gap-2 font-display text-2xl font-semibold tracking-normal text-slate-950 dark:text-foreground",
          className,
        )}
      >
        <span className="group-data-[collapsible=icon]:hidden">AI Signal</span>
        <span className="hidden size-8 items-center justify-center rounded-full border border-slate-200 bg-white font-sans text-[0.68rem] font-semibold text-slate-700 group-data-[collapsible=icon]:inline-flex dark:border-border dark:bg-muted/45 dark:text-foreground">
          AI
        </span>
      </span>
    ) : (
      <span
        className={cn(
          "inline-flex items-center font-display font-semibold tracking-normal text-slate-950 dark:text-foreground",
          variant === "full"
            ? "text-2xl sm:text-3xl"
            : "size-8 justify-center rounded-full border border-slate-200 bg-white font-sans text-[0.68rem] text-slate-700 dark:border-border dark:bg-muted/45 dark:text-foreground",
          className,
        )}
      >
        {variant === "full" ? "AI Signal" : "AI"}
      </span>
    )

  if (!asLink) {
    return content
  }

  return (
    <Link to="/" aria-label="AI Signal home">
      {content}
    </Link>
  )
}
