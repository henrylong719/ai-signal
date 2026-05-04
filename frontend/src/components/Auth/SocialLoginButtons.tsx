import { FaGithub } from "react-icons/fa"
import { FaXTwitter } from "react-icons/fa6"
import { FcGoogle } from "react-icons/fc"
import { ProviderButton } from "./AuthShared"

const socialProviders = [
  {
    label: "Google",
    icon: <FcGoogle className="size-5" />,
  },
  {
    label: "X",
    icon: <FaXTwitter className="size-4 text-slate-950" />,
  },
  {
    label: "GitHub",
    icon: <FaGithub className="size-5 text-[#24292f]" />,
  },
]

export function SocialLoginButtons({
  onProviderClick,
}: {
  onProviderClick: () => void
}) {
  return (
    <div className="mt-4 grid w-full gap-2">
      {socialProviders.map((provider) => (
        <ProviderButton
          compact
          icon={provider.icon}
          key={provider.label}
          onClick={onProviderClick}
        >
          Continue with {provider.label}
        </ProviderButton>
      ))}
    </div>
  )
}
