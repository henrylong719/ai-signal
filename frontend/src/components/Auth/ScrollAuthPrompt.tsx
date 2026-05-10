import { XIcon } from 'lucide-react'
import { useEffect, useState } from 'react'

import AuthFlow from '@/components/Auth/AuthFlow'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import useAuth from '@/hooks/useAuth'
import { trackGuestEvent } from '@/lib/analytics'
import { ARTICLE_FEED_LOAD_MORE_EVENT } from '@/lib/auth-prompt'

const DISMISSED_KEY = 'ai-signal-load-more-auth-prompt-dismissed'

function hasDismissedPrompt() {
  if (typeof window === 'undefined') return true
  return window.sessionStorage.getItem(DISMISSED_KEY) === '1'
}

function markPromptDismissed() {
  if (typeof window === 'undefined') return
  window.sessionStorage.setItem(DISMISSED_KEY, '1')
}

function ScrollAuthPrompt() {
  const { isLoading, user } = useAuth()
  const [dismissed, setDismissed] = useState(hasDismissedPrompt)
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    if (dismissed || isLoading || user) return

    const openPrompt = () => {
      // The scroll prompt is itself a sign-up CTA — it pops the auth
      // flow at a known funnel moment (reader hit the bottom of the
      // feed). Tag the event with its UI location so analytics can
      // compare it against the hero and header CTAs.
      trackGuestEvent('guest_signup_click', {
        payload: { metadata: { location: 'feed_sidebar' } },
      })
      setIsOpen(true)
    }
    window.addEventListener(ARTICLE_FEED_LOAD_MORE_EVENT, openPrompt)

    return () => {
      window.removeEventListener(ARTICLE_FEED_LOAD_MORE_EVENT, openPrompt)
    }
  }, [dismissed, isLoading, user])

  const handleOpenChange = (nextOpen: boolean) => {
    setIsOpen(nextOpen)

    if (!nextOpen) {
      markPromptDismissed()
      setDismissed(true)
    }
  }

  if (dismissed || isLoading || user) {
    return null
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent
        showCloseButton={false}
        overlayClassName="z-[70] bg-black/35 dark:bg-black/55"
        className="z-[80] max-h-[calc(100svh-1.5rem)] overflow-y-auto border border-slate-200/80 bg-white p-0 text-slate-950 shadow-xl dark:border-border dark:bg-card dark:text-card-foreground dark:shadow-[0_18px_45px_rgba(0,0,0,0.32),0_2px_8px_rgba(0,0,0,0.24)] sm:max-w-[500px] sm:rounded-lg"
      >
        <DialogTitle className="sr-only">AI Signal authentication</DialogTitle>
        <DialogDescription className="sr-only">
          Sign in or create an AI Signal account. You can close this and keep
          browsing.
        </DialogDescription>
        <AuthFlow
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

export default ScrollAuthPrompt
