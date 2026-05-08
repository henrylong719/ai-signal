import { MailIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { FaFacebook, FaGithub } from 'react-icons/fa'
import { FcGoogle } from 'react-icons/fc'
import { ProviderButton } from './AuthShared'

export type SocialAuthProvider = 'google' | 'github' | 'facebook'

const socialProviders = [
  {
    id: 'google',
    label: 'Google',
    icon: <FcGoogle className="size-5" />,
    emphasis: 'primary',
  },
  {
    id: 'github',
    label: 'GitHub',
    icon: <FaGithub className="size-5 text-[#24292f] dark:text-slate-100" />,
    emphasis: 'secondary',
  },
  {
    id: 'facebook',
    label: 'Facebook',
    icon: <FaFacebook className="size-5 text-[#1877f2]" />,
    emphasis: 'secondary',
  },
] satisfies {
  id: SocialAuthProvider
  label: string
  icon: ReactNode
  emphasis: 'primary' | 'secondary'
}[]

export function SocialLoginButtons({
  onEmailClick,
  onProviderClick,
}: {
  onEmailClick: () => void
  onProviderClick: (provider: SocialAuthProvider) => void
}) {
  return (
    <div className="grid w-full gap-2">
      {socialProviders.map((provider) => (
        <ProviderButton
          emphasis={provider.emphasis}
          icon={provider.icon}
          key={provider.label}
          onClick={() => onProviderClick(provider.id)}
        >
          Continue with {provider.label}
        </ProviderButton>
      ))}
      <ProviderButton
        icon={
          <MailIcon className="size-5 stroke-[1.8] text-slate-700 dark:text-foreground/78" />
        }
        onClick={onEmailClick}
      >
        Continue with email
      </ProviderButton>
    </div>
  )
}
