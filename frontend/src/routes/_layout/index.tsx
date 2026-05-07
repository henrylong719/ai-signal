import { createFileRoute, Link } from '@tanstack/react-router';
import { LogInIcon } from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import {
  ArticleList,
  ArticleListState,
} from '@/components/Articles/ArticleList';
import { MobileSidebar, Sidebar } from '@/components/Landing/Sidebar';
import { useArticleFeed } from '@/hooks/useArticleFeed';
import { useForYouFeed } from '@/hooks/useForYouFeed';
import useAuth from '@/hooks/useAuth';

export const Route = createFileRoute('/_layout/')({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: 'AI Signal',
      },
    ],
  }),
});

type Tab = 'for-you' | 'latest';

const tabs: { value: Tab; label: string }[] = [
  { value: 'for-you', label: 'For you' },
  { value: 'latest', label: 'Latest' },
];

function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('for-you');
  const feedTopRef = useRef<HTMLDivElement>(null);
  const latest = useArticleFeed();
  // useForYouFeed always runs, but its query needs auth — when the user
  // isn't logged in we render the sign-in CTA instead. Calling the hook
  // unconditionally keeps the hooks order stable.
  const forYou = useForYouFeed();
  const { user } = useAuth();

  // Build a stable id→reason map. ForYouArticle extends ArticlePublic so
  // the underlying article objects are compatible with ArticleList; the
  // reason is passed alongside via this map.
  const forYouReasons = useMemo(() => {
    const m = new Map<string, string | null>();
    for (const article of forYou.articles) {
      m.set(article.id, article.reason);
    }
    return m;
  }, [forYou.articles]);

  const handleTabChange = (tab: Tab) => {
    if (tab === activeTab) {
      return;
    }

    setActiveTab(tab);
    window.requestAnimationFrame(() => {
      feedTopRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });
  };

  return (
    <div className="grid w-full gap-8 lg:grid-cols-[minmax(0,1fr)_340px] xl:gap-12">
      <div className="min-w-0">
        <div
          ref={feedTopRef}
          className="scroll-mt-16 sm:scroll-mt-[72px]"
          aria-hidden="true"
        />
        <div className="sticky top-16 z-40 -mx-4 border-b border-slate-200/80 bg-white/95 px-4 pt-6 backdrop-blur sm:top-[72px] sm:-mx-6 sm:px-6 lg:mx-0 lg:px-0 dark:border-border dark:bg-background/92">
          <div className="flex items-center">
            <MobileSidebar />
            <div className="flex gap-8 sm:gap-10">
              {tabs.map((tab) => (
                <button
                  key={tab.value}
                  type="button"
                  onClick={() => handleTabChange(tab.value)}
                  className={`relative rounded-sm pb-5 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-4 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background ${
                    activeTab === tab.value
                      ? 'text-slate-950 dark:text-foreground'
                      : 'text-slate-500 hover:text-slate-800 dark:text-muted-foreground dark:hover:text-foreground/86'
                  }`}
                >
                  {tab.label}
                  {activeTab === tab.value && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-slate-950 dark:bg-primary" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {activeTab === 'for-you' &&
          (user ? (
            <ArticleList
              {...forYou}
              showDismiss
              reasons={forYouReasons}
              emptyTitle="No personalized signals yet"
              emptyDescription="Save a few articles or pick interests in Settings to start tailoring your feed."
            />
          ) : (
            <ArticleListState
              title="Sign in to personalize your feed"
              description="Your For You feed is built from articles you save, click, and the topics you tell us you care about."
              icon={<LogInIcon className="h-5 w-5 stroke-[1.5]" />}
              action={
                <Link
                  to="/login"
                  className="inline-flex h-9 items-center rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/88 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
                >
                  Sign in
                </Link>
              }
            />
          ))}
        {activeTab === 'latest' && <ArticleList {...latest} />}
      </div>
      <Sidebar />
    </div>
  );
}
