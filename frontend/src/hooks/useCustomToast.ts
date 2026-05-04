import { toast } from "sonner"

const useCustomToast = () => {
  const showSuccessToast = (description: string) => {
    toast.success(description)
  }

  const showErrorToast = (description: string) => {
    toast.error(description)
  }

  return { showSuccessToast, showErrorToast }
}

export default useCustomToast
