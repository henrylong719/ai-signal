import { MenuIcon, SparklesIcon } from 'lucide-react';
import { type CSSProperties, useLayoutEffect, useRef, useState } from 'react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import useAuth from '@/hooks/useAuth';
import ArticleSource from './ArticleSource';
import RecentBookmarks from './RecentBookmarks';
import RecommendedTopics from './RecommendedTopics';
import TodayDigest from './TodayDigest';

function SidebarSections() {
  const { user } = useAuth();

  return (
    <>
      <TodayDigest />
      <RecommendedTopics />
      <ArticleSource />
      {user && <RecentBookmarks />}
    </>
  );
}

export function MobileSidebar() {
  return (
    <div className="lg:hidden">
      <Sheet>
        <SheetTrigger asChild>
          <button
            type="button"
            aria-label="Open explore menu"
            className="mr-4 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-muted/45 dark:text-muted-foreground dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            <MenuIcon className="h-5 w-5 stroke-[1.7]" />
          </button>
        </SheetTrigger>

        <SheetContent
          side="left"
          className="w-[88vw] max-w-sm overflow-y-auto bg-white dark:bg-background"
        >
          <SheetHeader className="border-b border-slate-100 px-5 py-5 dark:border-border">
            <SheetTitle className="flex items-center gap-2 text-slate-950 dark:text-foreground">
              <SparklesIcon className="h-4 w-4 stroke-[1.8] text-slate-400 dark:text-muted-foreground" />
              Explore AI Signal
            </SheetTitle>
            <SheetDescription>
              Browse topics, sources, and saved articles.
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-8 px-5 pb-8 pt-5">
            <SidebarSections />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

export function Sidebar() {
  const sidebarRef = useRef<HTMLElement>(null);
  const [sidebarHeight, setSidebarHeight] = useState(0);

  useLayoutEffect(() => {
    const sidebar = sidebarRef.current;

    if (!sidebar) {
      return;
    }

    const updateHeight = () => {
      setSidebarHeight(Math.ceil(sidebar.getBoundingClientRect().height));
    };

    updateHeight();

    if (typeof ResizeObserver === 'undefined') {
      return;
    }

    const observer = new ResizeObserver(updateHeight);
    observer.observe(sidebar);

    return () => observer.disconnect();
  }, []);

  // When the rail is taller than the viewport, the negative top lets it
  // scroll with the page until its bottom edge reaches the viewport.
  const sidebarStyle: CSSProperties = {
    top:
      sidebarHeight > 0
        ? `min(6.5rem, calc(100vh - ${sidebarHeight}px - 2rem))`
        : '6.5rem',
  };

  return (
    <aside
      ref={sidebarRef}
      style={sidebarStyle}
      className="hidden self-start border-l border-slate-200/70 pb-8 pt-8 lg:sticky lg:block lg:w-[340px] lg:pl-10 dark:border-border/70"
    >
      <div className="space-y-10">
        <SidebarSections />
      </div>
    </aside>
  );
}
