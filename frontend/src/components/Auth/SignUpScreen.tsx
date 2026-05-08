import { ArrowLeftIcon } from 'lucide-react'
import type { UseFormReturn } from 'react-hook-form'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { LoadingButton } from '@/components/ui/loading-button'
import { PasswordInput } from '@/components/ui/password-input'
import { cn } from '@/lib/utils'
import { AuthIntro } from './AuthIntro'
import {
  AUTH_INPUT_CLASS,
  AUTH_LABEL_CLASS,
  primaryButtonClass,
} from './AuthShared'
import type { SignUpFormData } from './authSchemas'

interface SignUpScreenProps {
  form: UseFormReturn<SignUpFormData>
  loading: boolean
  onBackToProviders: () => void
  onSignIn: () => void
  onSubmit: (data: SignUpFormData) => void
}

export function SignUpScreen({
  form,
  loading,
  onBackToProviders,
  onSignIn,
  onSubmit,
}: SignUpScreenProps) {
  return (
    <div className="flex w-full flex-col items-center">
      <AuthIntro
        title="Create account with email"
        description="Add a few details to personalize your AI Signal account."
      />

      <button
        type="button"
        className="mt-5 inline-flex items-center gap-1.5 self-start text-sm font-medium text-slate-500 transition hover:text-slate-950 dark:text-muted-foreground dark:hover:text-foreground"
        onClick={onBackToProviders}
      >
        <ArrowLeftIcon className="size-4 stroke-[1.8]" />
        All options
      </button>

      <Form {...form}>
        <form className="mt-4 w-full" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="grid gap-4">
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem className="gap-2">
                  <FormLabel className={AUTH_LABEL_CLASS}>Full Name</FormLabel>
                  <FormControl>
                    <Input
                      autoComplete="name"
                      data-testid="full-name-input"
                      placeholder="Full Name"
                      type="text"
                      className={AUTH_INPUT_CLASS}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem className="gap-2">
                  <FormLabel className={AUTH_LABEL_CLASS}>Email</FormLabel>
                  <FormControl>
                    <Input
                      autoComplete="email"
                      data-testid="email-input"
                      placeholder="you@example.com"
                      type="email"
                      className={AUTH_INPUT_CLASS}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem className="gap-2">
                  <FormLabel className={AUTH_LABEL_CLASS}>Password</FormLabel>
                  <FormControl>
                    <PasswordInput
                      autoComplete="new-password"
                      data-testid="password-input"
                      placeholder="Password"
                      className={cn(AUTH_INPUT_CLASS, 'pr-12 sm:pr-16')}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <p className="mt-4 text-center text-xs leading-relaxed text-slate-500 dark:text-muted-foreground">
            By creating an account, you agree to AI Signal&apos;s terms and
            privacy practices.
          </p>

          <LoadingButton
            type="submit"
            loading={loading}
            className={cn(primaryButtonClass, 'mt-4')}
          >
            Create Account
          </LoadingButton>
        </form>
      </Form>

      <p className="mt-6 text-center text-sm text-slate-500 dark:text-muted-foreground">
        Already have an account?{' '}
        <button
          type="button"
          className="font-semibold text-slate-950 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/78"
          onClick={onSignIn}
        >
          Sign In
        </button>
      </p>
    </div>
  )
}
