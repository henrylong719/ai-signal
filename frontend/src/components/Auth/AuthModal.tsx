import { XIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { useCallback, useEffect, useState } from 'react'

import AuthFlow from '@/components/Auth/AuthFlow'
import type { AuthMode } from '@/components/Auth/authTypes'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import useAuth from '@/hooks/useAuth'

interface AuthModalProps {
  description?: string
  initialMode?: AuthMode
  onOpenChange?: (open: boolean) => void
  open?: boolean
  title?: string
  trigger?: ReactNode
}

function AuthModal({
  description,
  initialMode = 'sign-in',
  onOpenChange,
  open,
  title,
  trigger,
}: AuthModalProps) {
  const { user } = useAuth()
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false)
  const isOpen = open ?? uncontrolledOpen
  const triggerContent =
    trigger === undefined ? (
      <Button
        variant="ghost"
        size="sm"
        className="inline-flex h-9 rounded-full border border-slate-200 bg-white px-4 font-medium text-slate-700 shadow-sm hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:ring-slate-950/15 dark:border-border dark:bg-muted/45 dark:text-foreground/86 dark:shadow-none dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35"
      >
        Sign In
      </Button>
    ) : (
      trigger
    )

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (open === undefined) {
        setUncontrolledOpen(nextOpen)
      }
      onOpenChange?.(nextOpen)
    },
    [onOpenChange, open],
  )

  useEffect(() => {
    if (user) {
      handleOpenChange(false)
    }
  }, [handleOpenChange, user])

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      {triggerContent && (
        <DialogTrigger asChild>{triggerContent}</DialogTrigger>
      )}
      <DialogContent
        showCloseButton={false}
        overlayClassName="z-[70] bg-black/40 dark:bg-black/55"
        className="z-80 max-h-[calc(100svh-1.5rem)] overflow-y-auto border border-slate-200/80 bg-white p-0 text-slate-950 shadow-xl dark:border-border dark:bg-card dark:text-card-foreground dark:shadow-[0_18px_45px_rgba(0,0,0,0.32),0_2px_8px_rgba(0,0,0,0.24)] sm:max-w-125 sm:rounded-lg"
      >
        <DialogTitle className="sr-only">AI Signal authentication</DialogTitle>
        <DialogDescription className="sr-only">
          Sign in or create an AI Signal account.
        </DialogDescription>
        <AuthFlow
          description={description}
          initialMode={initialMode}
          title={title}
          closeControl={
            <DialogClose className="absolute right-5 top-5 z-10 rounded-sm p-1.5 text-slate-500 transition hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 dark:text-muted-foreground dark:hover:text-foreground dark:focus-visible:ring-ring/35">
              <XIcon className="size-5 stroke-[1.6]" />
              <span className="sr-only">Close</span>
            </DialogClose>
          }
        />
      </DialogContent>
    </Dialog>
  )
}

export default AuthModal
