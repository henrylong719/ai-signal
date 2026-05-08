import { createFileRoute, Outlet } from '@tanstack/react-router'
import ScrollAuthPrompt from '@/components/Auth/ScrollAuthPrompt'
import Header from '@/components/Common/Header'

export const Route = createFileRoute('/_layout')({
  component: Layout,
})

function Layout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <main className="px-4 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-[1480px]">
          <Outlet />
        </div>
      </main>
      <ScrollAuthPrompt />
    </div>
  )
}

export default Layout
