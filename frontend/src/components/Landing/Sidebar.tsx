import { MenuIcon, SparklesIcon } from 'lucide-react';
import { type CSSProperties, useLayoutEffect, useRef, useState } from 'react';
import { SupportFooterLinks } from '@/components/Legal/SupportFooterLinks';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import ArticleSource from './ArticleSource';
import RecommendedTopics from './RecommendedTopics';
import TodayDigest from './TodayDigest';

function SidebarSections() {
  return (
    <>
      <TodayDigest />
      <RecommendedTopics />
      <ArticleSource />
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
            aria-label="Open navigation"
            className="mr-4 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:border-border dark:bg-muted/45 dark:text-muted-foreground dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            <MenuIcon className="h-5 w-5 stroke-[1.7]" />
          </button>
        </SheetTrigger>

        <SheetContent
          side="left"
          className="w-[88vw] max-w-90 gap-0 overflow-y-auto bg-white dark:bg-background [&>button]:right-4 [&>button]:top-4 [&>button]:flex [&>button]:h-9 [&>button]:w-9 [&>button]:items-center [&>button]:justify-center [&>button]:rounded-md [&>button]:text-slate-500 [&>button]:opacity-100 [&>button]:hover:bg-slate-100 [&>button]:hover:text-slate-950 [&>button]:focus:ring-slate-950/10 [&>button]:focus:ring-offset-0 dark:[&>button]:text-muted-foreground dark:[&>button]:hover:bg-accent dark:[&>button]:hover:text-foreground dark:[&>button]:focus:ring-ring/25"
        >
          <SheetHeader className="border-b border-slate-100 px-5 py-4 pr-16 dark:border-border">
            <SheetTitle className="flex items-center gap-2 text-[1.05rem] leading-6 text-slate-950 dark:text-foreground">
              <SparklesIcon className="h-4 w-4 stroke-[1.8] text-slate-400 dark:text-muted-foreground" />
              Explore AI Signal
            </SheetTitle>
            <SheetDescription className="text-[0.8125rem] leading-5">
              Browse topics, sources, and saved articles.
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-6 px-5 pb-7 pt-4">
            <SidebarSections />
            <div className="border-t border-slate-200/70 pt-5 dark:border-border">
              <SupportFooterLinks variant="wrap" withCopyright />
            </div>
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
      className="hidden self-start border-l border-slate-200/70 lg:sticky lg:block lg:w-[320px] lg:pl-8 dark:border-border/70"
    >
      <div className="divide-y divide-slate-200/70 *:py-7 [&>*:first-child]:pt-5 [&>*:last-child]:pb-5 dark:divide-border">
        <SidebarSections />
      </div>
      <div className="border-t border-slate-200/70 pb-5 pt-5 dark:border-border/70">
        <SupportFooterLinks variant="wrap" withCopyright />
      </div>
    </aside>
  );
}
