import { Link as RouterLink } from '@tanstack/react-router'
import { ArrowLeftIcon } from 'lucide-react'
import type { UseFormReturn } from 'react-hook-form'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
import type { LoginFormData } from './authSchemas'

interface SignInScreenProps {
  errorMessage?: string
  form: UseFormReturn<LoginFormData>
  loading: boolean
  onBackToProviders: () => void
  onCreateAccount: () => void
  onSubmit: (data: LoginFormData) => void
}

export function SignInScreen({
  errorMessage,
  form,
  loading,
  onBackToProviders,
  onCreateAccount,
  onSubmit,
}: SignInScreenProps) {
  return (
    <div className="flex w-full flex-col items-center">
      <AuthIntro
        title="Sign in with email"
        description="Use the email and password connected to your account."
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
              name="username"
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
                      autoComplete="current-password"
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

          <div className="mt-4 flex justify-end">
            <RouterLink
              to="/recover-password"
              className="text-sm font-normal text-slate-600 hover:text-slate-950 dark:text-muted-foreground dark:hover:text-foreground"
            >
              Forgot password?
            </RouterLink>
          </div>

          {errorMessage && (
            <Alert
              variant="destructive"
              className="mt-4 rounded-[6px] px-3 py-2"
            >
              <AlertDescription className="text-sm leading-relaxed">
                {errorMessage}
              </AlertDescription>
            </Alert>
          )}

          <LoadingButton
            type="submit"
            loading={loading}
            className={cn(primaryButtonClass, 'mt-4')}
          >
            Sign In
          </LoadingButton>
        </form>
      </Form>

      <p className="mt-6 text-center text-sm text-slate-500 dark:text-muted-foreground">
        Don&apos;t have an account?{' '}
        <button
          type="button"
          className="font-semibold text-slate-950 hover:text-slate-700 dark:text-foreground dark:hover:text-foreground/78"
          onClick={onCreateAccount}
        >
          Create one
        </button>
      </p>
    </div>
  )
}
