import { Link as RouterLink } from "@tanstack/react-router"
import type { UseFormReturn } from "react-hook-form"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import { cn } from "@/lib/utils"
import { AuthIntro } from "./AuthIntro"
import {
  AUTH_INPUT_CLASS,
  AUTH_LABEL_CLASS,
  primaryButtonClass,
} from "./AuthShared"
import type { LoginFormData } from "./authSchemas"
import { SocialLoginButtons } from "./SocialLoginButtons"

interface SignInScreenProps {
  form: UseFormReturn<LoginFormData>
  loading: boolean
  onCreateAccount: () => void
  onSocialProviderClick: () => void
  onSubmit: (data: LoginFormData) => void
  remember: boolean
  setRemember: (remember: boolean) => void
}

export function SignInScreen({
  form,
  loading,
  onCreateAccount,
  onSocialProviderClick,
  onSubmit,
}: SignInScreenProps) {
  return (
    <div className="flex w-full flex-col items-center">
      <AuthIntro
        title="Welcome back"
        description="Sign in to continue tracking the latest AI signals."
      />

      <Form {...form}>
        <form className="mt-6 w-full" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="grid gap-5">
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem className="gap-3">
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
                <FormItem className="gap-3">
                  <FormLabel className={AUTH_LABEL_CLASS}>Password</FormLabel>
                  <FormControl>
                    <PasswordInput
                      autoComplete="current-password"
                      data-testid="password-input"
                      placeholder="Password"
                      className={cn(AUTH_INPUT_CLASS, "pr-12 sm:pr-16")}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            {/* <label
              htmlFor={rememberId}
              className="flex items-center gap-2 text-sm text-slate-600"
            >
              <Checkbox
                checked={remember}
                className="size-4 rounded-[3px] border-slate-400 data-[state=checked]:border-slate-950 data-[state=checked]:bg-slate-950 data-[state=checked]:text-white"
                id={rememberId}
                onCheckedChange={(value) => setRemember(value === true)}
              />
              Remember me
            </label> */}

            <RouterLink
              to="/recover-password"
              className="text-sm font-normal text-blue-600 hover:text-blue-700"
            >
              Forgot password?
            </RouterLink>
          </div>

          <LoadingButton
            type="submit"
            loading={loading}
            className={cn(primaryButtonClass, "mt-6")}
          >
            Sign In
          </LoadingButton>

          <SocialLoginButtons onProviderClick={onSocialProviderClick} />
        </form>
      </Form>

      <p className="mt-5 text-center text-sm text-slate-500">
        Don&apos;t have an account?{" "}
        <button
          type="button"
          className="font-semibold text-slate-950 hover:text-blue-700"
          onClick={onCreateAccount}
        >
          Create one
        </button>
      </p>
    </div>
  )
}
