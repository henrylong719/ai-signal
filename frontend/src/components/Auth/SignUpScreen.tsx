import { useState } from "react"
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
import type { SignUpFormData } from "./authSchemas"
import {
  type SocialAuthProvider,
  SocialLoginButtons,
} from "./SocialLoginButtons"

const topics = [
  "AI Agents",
  "RAG",
  "LLM Tools",
  "MCP",
  "Research",
  "Voice AI",
  "Evals",
  "Startups",
]

interface SignUpScreenProps {
  form: UseFormReturn<SignUpFormData>
  loading: boolean
  onSignIn: () => void
  onSocialProviderClick: (provider: SocialAuthProvider) => void
  onSubmit: (data: SignUpFormData) => void
}

export function SignUpScreen({
  form,
  loading,
  onSignIn,
  onSocialProviderClick,
  onSubmit,
}: SignUpScreenProps) {
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])

  const toggleTopic = (topic: string) => {
    setSelectedTopics((currentTopics) =>
      currentTopics.includes(topic)
        ? currentTopics.filter((currentTopic) => currentTopic !== topic)
        : [...currentTopics, topic],
    )
  }

  return (
    <div className="flex w-full flex-col items-center">
      <AuthIntro
        title="Create your account"
        description="Save articles, personalize topics, and receive daily AI insights."
      />

      <Form {...form}>
        <form className="mt-6 w-full" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="grid gap-5">
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem className="gap-3">
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

            <div className="grid gap-5 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem className="gap-3">
                    <FormLabel className={AUTH_LABEL_CLASS}>Password</FormLabel>
                    <FormControl>
                      <PasswordInput
                        autoComplete="new-password"
                        data-testid="password-input"
                        placeholder="Password"
                        className={cn(AUTH_INPUT_CLASS, "pr-12 sm:pr-14")}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem className="gap-3">
                    <FormLabel className={AUTH_LABEL_CLASS}>
                      Confirm Password
                    </FormLabel>
                    <FormControl>
                      <PasswordInput
                        autoComplete="new-password"
                        data-testid="confirm-password-input"
                        placeholder="Confirm password"
                        className={cn(AUTH_INPUT_CLASS, "pr-12 sm:pr-14")}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </div>

          <div className="my-5 h-px w-full bg-slate-200 dark:bg-slate-800" />

          <div className="w-full">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              Topics of Interest (Optional)
            </h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {topics.map((topic) => {
                const selected = selectedTopics.includes(topic)

                return (
                  <button
                    type="button"
                    aria-pressed={selected}
                    className={cn(
                      "rounded-full border px-3 py-1 text-xs font-semibold transition sm:px-4 sm:py-1.5 sm:text-sm",
                      selected
                        ? "border-slate-950 bg-slate-950 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-950"
                        : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-slate-600",
                    )}
                    key={topic}
                    onClick={() => toggleTopic(topic)}
                  >
                    {topic}
                  </button>
                )
              })}
            </div>
          </div>

          <LoadingButton
            type="submit"
            loading={loading}
            className={cn(primaryButtonClass, "mt-6")}
          >
            Create Account
          </LoadingButton>

          <SocialLoginButtons onProviderClick={onSocialProviderClick} />
        </form>
      </Form>

      <p className="mt-5 text-center text-sm text-slate-500 dark:text-slate-400">
        Already have an account?{" "}
        <button
          type="button"
          className="font-semibold text-slate-950 hover:text-blue-700 dark:text-slate-100 dark:hover:text-cyan-200"
          onClick={onSignIn}
        >
          Sign In
        </button>
      </p>
    </div>
  )
}
