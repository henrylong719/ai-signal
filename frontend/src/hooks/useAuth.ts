import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import {
  type Body_login_login_access_token as AccessToken,
  LoginService,
  type UserPublic,
  type UserRegister,
  UsersService,
} from "@/client"
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "@/lib/auth-token"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

const isLoggedIn = () => {
  return getAccessToken() !== ""
}

type LoginCredentials = AccessToken & {
  remember?: boolean
}

const useAuth = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

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

  const login = async ({ remember = true, ...data }: LoginCredentials) => {
    const response = await LoginService.loginAccessToken({
      formData: data,
    })
    setAccessToken(response.access_token, remember)
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ to: "/" })
    },
    onError: handleError.bind(showErrorToast),
  })

  const logout = () => {
    clearAccessToken()
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
