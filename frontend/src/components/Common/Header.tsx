import { Link } from '@tanstack/react-router';
import { SearchIcon } from 'lucide-react';
import AuthModal from '../Auth/AuthModal';
import useAuth from '@/hooks/useAuth';
import { HeaderActionsMenu } from './HeaderActionsMenu';

const Header = () => {
  const { user: currentUser } = useAuth();

  return (
    <header className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto h-20 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 group">
            <span className="font-serif font-medium text-3xl tracking-tight">
              AI Signal
            </span>
          </Link>

          <div className="relative hidden sm:block">
            <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-slate-400 stroke-[1.5]" />
            <input
              type="text"
              placeholder="Search..."
              className="h-10 w-60 rounded-full bg-slate-50 border-transparent focus:bg-white focus:border-slate-200 pl-9 pr-4 text-sm outline-none transition-all placeholder:text-slate-400"
            />
          </div>
        </div>

        <div className="flex items-center gap-4">
          {currentUser ? <HeaderActionsMenu /> : <AuthModal />}
        </div>
      </div>
    </header>
  );
};

export default Header;
