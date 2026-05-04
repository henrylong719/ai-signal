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
    <>
      {/* <AppSidebar /> */}

      {/* <SidebarInset> */}
      <Header />
      <main className="px-6 md:px-8">
        <div className="mx-auto">
          <Outlet />
        </div>
      </main>
      {/* <Footer /> */}
      {/* </SidebarInset> */}
    </>
  )
}

export default Layout
