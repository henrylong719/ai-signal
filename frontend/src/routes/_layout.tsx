import { createFileRoute, Outlet, redirect } from '@tanstack/react-router';

import { Footer } from '@/components/Common/Footer';
import AppSidebar from '@/components/Sidebar/AppSidebar';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { isLoggedIn } from '@/hooks/useAuth';
import Header from '@/components/Common/Header';

export const Route = createFileRoute('/_layout')({
  component: Layout,
  beforeLoad: async () => {
    // if (!isLoggedIn()) {
    //   throw redirect({
    //     to: '/login',
    //   });
    // }
  },
});

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
  );
}

export default Layout;
