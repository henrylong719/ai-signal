import { Link as RouterLink } from '@tanstack/react-router';
import {
  Bookmark,
  Check,
  ChevronDown,
  LogOut,
  Monitor,
  Moon,
  Settings,
  Sun,
  UserStar,
} from 'lucide-react';
import { useState } from 'react';
import { type Theme, useTheme } from '@/components/theme-provider';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import useAuth from '@/hooks/useAuth';
import { getInitials } from '@/utils';
import { Avatar, AvatarFallback } from '../ui/avatar';

interface UserInfoProps {
  fullName?: string;
  email?: string;
}

function UserInfo({ fullName, email }: UserInfoProps) {
  const displayName = fullName?.trim() || 'AI Signal reader';
  const initialsSource = fullName?.trim() || email || 'User';

  return (
    <div className="flex min-w-0 items-center gap-3">
      <Avatar className="size-10 border border-slate-200 bg-slate-950 shadow-sm dark:border-border dark:bg-primary">
        <AvatarFallback className="bg-slate-950 text-xs font-semibold text-white dark:bg-primary dark:text-primary-foreground">
          {getInitials(initialsSource)}
        </AvatarFallback>
      </Avatar>
      <div className="flex min-w-0 flex-col items-start">
        <p className="w-full truncate text-sm font-semibold text-slate-950 dark:text-foreground">
          {displayName}
        </p>
        {email && (
          <p className="mt-0.5 w-full truncate text-xs text-slate-500 dark:text-muted-foreground">
            {email}
          </p>
        )}
      </div>
    </div>
  );
}

const themeOptions: { value: Theme; label: string; icon: typeof Monitor }[] = [
  { value: 'system', label: 'System Default', icon: Monitor },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
];

export const HeaderActionsMenu = () => {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const { setTheme, theme } = useTheme();
  const initialsSource = user?.full_name?.trim() || user?.email || 'User';
  const currentTheme = themeOptions.find((option) => option.value === theme);
  const CurrentThemeIcon = currentTheme?.icon ?? Monitor;

  const handleLogout = () => {
    void logout();
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Open profile menu"
          className="group inline-flex h-10 items-center gap-1 rounded-full border border-slate-200 bg-white py-1 pl-1 pr-2 text-slate-500 shadow-sm transition-all hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 data-[state=open]:border-slate-300 data-[state=open]:bg-slate-50 dark:border-border dark:bg-muted/45 dark:text-muted-foreground dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background dark:data-[state=open]:border-foreground/18 dark:data-[state=open]:bg-accent"
        >
          <Avatar className="size-8 border border-white bg-slate-950 shadow-sm dark:border-border dark:bg-primary">
            <AvatarFallback className="bg-slate-950 text-[0.68rem] font-semibold text-white dark:bg-primary dark:text-primary-foreground">
              {getInitials(initialsSource)}
            </AvatarFallback>
          </Avatar>
          <ChevronDown className="h-3.5 w-3.5 stroke-[1.8] transition-transform duration-150 group-data-[state=open]:rotate-180" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        className="w-72 rounded-lg border-slate-200/80 bg-white p-2 shadow-[0_18px_45px_rgba(15,23,42,0.12),0_2px_8px_rgba(15,23,42,0.06)] dark:border-border dark:bg-popover dark:shadow-[0_18px_45px_rgba(0,0,0,0.28),0_2px_8px_rgba(0,0,0,0.22)]"
        side={'bottom'}
        align="end"
        sideOffset={10}
      >
        <DropdownMenuLabel className="px-2 pb-3 pt-2 font-normal">
          <UserInfo fullName={user?.full_name || ''} email={user?.email} />
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="-mx-2 my-1.5 bg-slate-100 dark:bg-border" />

        {user?.is_superuser && (
          <DropdownMenuItem
            asChild
            className="h-10 rounded-md px-2.5 text-[0.925rem] font-medium text-slate-700 transition-colors focus:bg-slate-50 focus:text-slate-950 data-[highlighted]:bg-slate-50 dark:text-foreground/86 dark:focus:bg-accent dark:focus:text-foreground dark:data-[highlighted]:bg-accent [&_svg]:text-slate-400 dark:[&_svg]:text-muted-foreground"
          >
            <RouterLink to="/admin">
              <UserStar className="h-4 w-4 stroke-[1.7]" />
              Admin
            </RouterLink>
          </DropdownMenuItem>
        )}

        <DropdownMenuItem
          asChild
          className="h-10 rounded-md px-2.5 text-[0.925rem] font-medium text-slate-700 transition-colors focus:bg-slate-50 focus:text-slate-950 data-[highlighted]:bg-slate-50 dark:text-foreground/86 dark:focus:bg-accent dark:focus:text-foreground dark:data-[highlighted]:bg-accent [&_svg]:text-slate-400 dark:[&_svg]:text-muted-foreground"
        >
          <RouterLink to="/saved-articles">
            <Bookmark className="h-4 w-4 stroke-[1.7]" />
            Your library
          </RouterLink>
        </DropdownMenuItem>

        <DropdownMenuItem
          asChild
          className="h-10 rounded-md px-2.5 text-[0.925rem] font-medium text-slate-700 transition-colors focus:bg-slate-50 focus:text-slate-950 data-[highlighted]:bg-slate-50 dark:text-foreground/86 dark:focus:bg-accent dark:focus:text-foreground dark:data-[highlighted]:bg-accent [&_svg]:text-slate-400 dark:[&_svg]:text-muted-foreground"
        >
          <RouterLink to="/settings">
            <Settings className="h-4 w-4 stroke-[1.7]" />
            Settings
          </RouterLink>
        </DropdownMenuItem>
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="h-10 rounded-md px-2.5 text-[0.925rem] font-medium text-slate-700 transition-colors focus:bg-slate-50 focus:text-slate-950 data-[state=open]:bg-slate-50 dark:text-foreground/86 dark:focus:bg-accent dark:focus:text-foreground dark:data-[state=open]:bg-accent [&_svg]:text-slate-400 dark:[&_svg]:text-muted-foreground">
            <CurrentThemeIcon className="h-4 w-4 stroke-[1.7] mr-2" />
            Appearance
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent className="min-w-52 rounded-lg border-slate-200/80 bg-white p-2 shadow-[0_18px_45px_rgba(15,23,42,0.12),0_2px_8px_rgba(15,23,42,0.06)] dark:border-border dark:bg-popover dark:shadow-[0_18px_45px_rgba(0,0,0,0.28),0_2px_8px_rgba(0,0,0,0.22)]">
            {themeOptions.map((option) => {
              const OptionIcon = option.icon;
              return (
                <DropdownMenuItem
                  key={option.value}
                  onClick={() => setTheme(option.value)}
                  className="h-10 rounded-md px-2.5 text-[0.925rem] font-medium text-slate-700 transition-colors focus:bg-slate-50 focus:text-slate-950 data-[highlighted]:bg-slate-50 dark:text-foreground/86 dark:focus:bg-accent dark:focus:text-foreground dark:data-[highlighted]:bg-accent [&_svg]:text-slate-400 dark:[&_svg]:text-muted-foreground"
                >
                  {theme === option.value ? (
                    <Check className="h-4 w-4 stroke-[1.9]" />
                  ) : (
                    <OptionIcon className="h-4 w-4 stroke-[1.7] opacity-0" />
                  )}
                  {option.label}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuSubContent>
        </DropdownMenuSub>
        <DropdownMenuSeparator className="-mx-2 my-1.5 bg-slate-100 dark:bg-border" />
        <DropdownMenuItem
          onClick={handleLogout}
          className="h-10 rounded-md px-2.5 text-[0.925rem] font-medium text-slate-500 transition-colors focus:bg-slate-50 focus:text-slate-900 data-[highlighted]:bg-slate-50 dark:text-muted-foreground dark:focus:bg-accent dark:focus:text-foreground dark:data-[highlighted]:bg-accent [&_svg]:text-slate-400 dark:[&_svg]:text-muted-foreground"
        >
          <LogOut className="h-4 w-4 stroke-[1.7]" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
