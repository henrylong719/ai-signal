import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import axios from "axios"

import {
  type Body_login_login_access_token as AccessToken,
  LoginService,
  OpenAPI,
  type UserPublic,
  type UserRegister,
  UsersService,
} from "@/client"
import { clearLoginState, isLoggedIn } from "@/lib/auth-state"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

const useAuth = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  // currentUser query is gated on the marker cookie. The server still
  // does its own auth check — the marker is only for UI suppression.
  const {
    data: user,
    isLoading,
    isError,
  } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) =>
      UsersService.registerUser({ requestBody: data }),
    onSuccess: () => {
      navigate({ to: "/login" })
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  // Login no longer reads the response body — the access cookie is set
  // server-side via Set-Cookie headers. The SDK call still works because
  // the backend continues to return the JSON token shape for backward
  // compatibility with non-browser callers (CLI, tests).
  //
  // The `remember` flag is accepted but ignored: with cookie auth, the
  // refresh cookie's 30-day TTL handles long-term sessions automatically.
  // The "Remember me" checkbox in SignInScreen is now decorative;
  // follow-up work should remove it from the UI to avoid the implicit
  // promise that unchecking it shortens the session.
  const login = async (
    data: AccessToken & { remember?: boolean },
  ): Promise<void> => {
    const { remember: _ignored, ...credentials } = data
    await LoginService.loginAccessToken({ formData: credentials })
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      // After login the marker cookie is set — invalidate any cached
      // queries that were gated on logged-in state.
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
      navigate({ to: "/" })
    },
    onError: handleError.bind(showErrorToast),
  })

  // Logout calls the server endpoint to clear all three auth cookies.
  // Best-effort: if the server is unreachable we still clear local state
  // and navigate, because leaving a stale "logged in" UI after an
  // explicit logout would be worse than swallowing the network error.
  // TODO: replace bare axios call with LoginService.logout() once the
  //   SDK is regenerated against the updated backend spec.
  const logout = async () => {
    try {
      await axios.post(`${OpenAPI.BASE}/api/v1/login/logout`, undefined, {
        withCredentials: true,
      })
    } catch {
      // Network error or server down — keep going, clear client state.
    }
    clearLoginState()
    queryClient.setQueryData(["currentUser"], null)
    queryClient.clear()
    navigate({ to: "/" })
  }

  return {
    signUpMutation,
    loginMutation,
    logout,
    user,
    isLoading,
    isError,
  }
}

export { isLoggedIn }
export default useAuth
