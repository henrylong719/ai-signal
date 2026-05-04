import { createFileRoute, redirect } from "@tanstack/react-router"

import AuthFlow from "@/components/Auth/AuthFlow"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Sign Up - AI Signal",
      },
    ],
  }),
})

function SignUp() {
  return (
    <main className="min-h-svh bg-white text-zinc-900">
      <AuthFlow initialMode="sign-up" className="mx-auto min-h-svh max-w-230" />
    </main>
  )
}
