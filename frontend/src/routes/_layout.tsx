import { createFileRoute, Outlet } from "@tanstack/react-router"
import Header from "@/components/Common/Header"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    // if (!isLoggedIn()) {
    //   throw redirect({
    //     to: '/login',
    //   });
    // }
  },
})

function Layout() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      {/* <AppSidebar /> */}

      {/* <SidebarInset> */}
      <Header />
      <main className="px-4 sm:px-6 md:px-8">
        <div className="mx-auto">
          <Outlet />
        </div>
      </main>
      {/* <Footer /> */}
      {/* </SidebarInset> */}
    </div>
  )
}

export default Layout
