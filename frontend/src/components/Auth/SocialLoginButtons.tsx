import type { ReactNode } from 'react'
import { FaGithub } from 'react-icons/fa'
import { FcGoogle } from 'react-icons/fc'
import { ProviderButton } from './AuthShared'

export type SocialAuthProvider = 'google' | 'github'

const socialProviders = [
  {
    id: 'google',
    label: 'Google',
    icon: <FcGoogle className="size-5" />,
  },
  {
    id: 'github',
    label: 'GitHub',
    icon: <FaGithub className="size-5 text-[#24292f] dark:text-slate-100" />,
  },
] satisfies {
  id: SocialAuthProvider
  label: string
  icon: ReactNode
}[]

export function SocialLoginButtons({
  onProviderClick,
}: {
  onProviderClick: (provider: SocialAuthProvider) => void
}) {
  return (
    <div className="mt-4 grid w-full gap-2">
      {socialProviders.map((provider) => (
        <ProviderButton
          compact
          icon={provider.icon}
          key={provider.label}
          onClick={() => onProviderClick(provider.id)}
        >
          Continue with {provider.label}
        </ProviderButton>
      ))}
    </div>
  )
}
