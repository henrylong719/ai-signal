import { type FormEvent, useState } from 'react'
import { Button } from '@/components/ui/button'
import { useSubscribe } from '@/hooks/useSubscribe'

function SubscribeBox() {
  const [email, setEmail] = useState('')
  const { submit, isSubmitting, isSuccess, reset } = useSubscribe()

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = email.trim()
    if (!trimmed || isSubmitting) {
      return
    }
    submit(
      { email: trimmed },
      {
        onSuccess: () => {
          setEmail('')
        },
      },
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-5 flex flex-col items-start justify-between gap-6 border-slate-100 border-y py-8 md:flex-row md:items-center dark:border-border"
    >
      <div>
        <h3 className="mb-1 font-medium font-sans text-slate-900 text-sm uppercase tracking-wider dark:text-foreground">
          Get the daily digest
        </h3>
        <p className="text-slate-500 text-sm dark:text-muted-foreground">
          The most important AI engineering updates, in your inbox.
        </p>
      </div>
      <div className="flex w-full gap-3 md:w-auto">
        <input
          type="email"
          required
          autoComplete="email"
          placeholder="Email address"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value)
            if (isSuccess) {
              reset()
            }
          }}
          disabled={isSubmitting}
          className="h-10 flex-1 rounded-full border border-transparent bg-slate-50 px-4 text-slate-900 text-sm outline-none transition-all placeholder:text-slate-400 focus:border-slate-200 focus:bg-white disabled:opacity-60 md:w-64 dark:bg-muted dark:text-foreground dark:placeholder:text-muted-foreground/70 dark:focus:border-border dark:focus:bg-card"
        />
        <Button
          type="submit"
          disabled={isSubmitting || email.trim().length === 0}
          className="rounded-full bg-slate-900 px-6 font-normal text-sm text-white hover:bg-slate-800 dark:bg-foreground dark:text-background dark:hover:bg-foreground/90"
        >
          {isSubmitting ? 'Subscribing…' : 'Subscribe'}
        </Button>
      </div>
    </form>
  )
}

export default SubscribeBox
