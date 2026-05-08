import { Home, SlidersHorizontal, Users } from 'lucide-react'

import { SidebarAppearance } from '@/components/Common/Appearance'
import { Logo } from '@/components/Common/Logo'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from '@/components/ui/sidebar'
import useAuth from '@/hooks/useAuth'
import { Main, type NavItem } from './Main'

// Dashboard is always present; "Tune your signal" is added for logged-in
// users (anonymous visitors get redirected to login from the route, so
// putting it in the nav for them would be confusing). Admin link only
// appears for superusers.
const baseItems: NavItem[] = [{ icon: Home, title: 'Dashboard', path: '/' }]

const personalizationItem: NavItem = {
  icon: SlidersHorizontal,
  title: 'Tune your signal',
  path: '/personalization',
}

const adminItem: NavItem = { icon: Users, title: 'Admin', path: '/admin' }

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const items: NavItem[] = currentUser
    ? currentUser.is_superuser
      ? [...baseItems, personalizationItem, adminItem]
      : [...baseItems, personalizationItem]
    : baseItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
