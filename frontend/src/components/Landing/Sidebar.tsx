import { Link } from '@tanstack/react-router';
import { Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { capitalized } from '@/lib/utils';
import { CATEGORIES } from '@/lib/constants';

export function Sidebar() {
  return (
    <aside className="pt-8 hidden lg:block lg:col-span-4 space-y-10 border-l border-slate-100 flex-0 lg:pl-10 md:flex-2">
      {/* Today's Digest Card */}
      {/* <div className="bg-slate-50 rounded-xl p-6 border-0">
        <div className="flex items-center gap-2 text-slate-500 mb-3">
          <CalendarIcon className="w-4 h-4 stroke-[1.5]" />
          <span className="text-xs font-medium uppercase tracking-wider font-sans">
            Today's Digest
          </span>
        </div>
        <h3 className="font-serif text-xl font-medium text-slate-900 mb-2">
          Significant leaps in multi-agent orchestration
        </h3>
        <p className="text-sm text-slate-600 mb-5 leading-relaxed font-serif">
          Plus, a new open-source eval framework gaining traction, and
          Anthropic's latest thoughts on context caching.
        </p>
        <Link
          to="/"
          className="inline-flex items-center text-sm font-sans font-medium text-slate-900 hover:text-slate-600 transition-colors"
        >
          Read the daily digest{' '}
          <ChevronRightIcon className="w-4 h-4 ml-1 stroke-[1.5]" />
        </Link>
      </div> */}

      {/* Saved Articles Shortcut */}
      {/* <div>
        <Link
          to="/"
          className="group flex items-center justify-between py-3 border-b border-slate-100 hover:border-slate-200 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="text-slate-400 group-hover:text-slate-900 transition-colors">
              <BookmarkIcon className="w-5 h-5 stroke-[1.5]" />
            </div>
            <span className="font-medium text-slate-900 font-sans text-sm">
              Your Saved Articles
            </span>
          </div>
          <ChevronRightIcon className="w-4 h-4 text-slate-300 group-hover:text-slate-900 transition-colors" />
        </Link>
      </div> */}

      {/* Trending Topics */}
      <div>
        <h3 className="font-sans text-xs font-medium uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
          <Sparkles className="w-4 h-4 stroke-[1.5]" /> Recommended topics
        </h3>
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((cat) => (
            <Link key={cat} to={`/category-feed/$cat`} params={{ cat: cat }}>
              <Badge
                variant="secondary"
                className="font-sans font-normal text-sm text-slate-900 bg-slate-100 border-transparent hover:bg-slate-200 px-6 py-2 cursor-pointer"
              >
                {capitalized(cat)}
              </Badge>
            </Link>
          ))}
        </div>
      </div>

      {/* Popular Signals */}
      {/* <div className="pt-4">
        <h3 className="font-sans text-xs font-medium uppercase tracking-wider text-slate-400 mb-5">
          Popular This Week
        </h3>
      </div> */}
    </aside>
  );
}
