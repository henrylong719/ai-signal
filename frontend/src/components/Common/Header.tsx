import { Link, useNavigate } from '@tanstack/react-router';
import { Check, Library, Monitor, Moon, SearchIcon, Sun } from 'lucide-react';
import { useState } from 'react';
import { type UseFormReturn, useForm } from 'react-hook-form';
import { PageContainer } from '@/components/Layout/Page';
import { type Theme, useTheme } from '@/components/theme-provider';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import useAuth from '@/hooks/useAuth';
import AuthModal from '../Auth/AuthModal';
import { Form, FormControl, FormField, FormItem } from '../ui/form';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '../ui/sheet';
import { HeaderActionsMenu } from './HeaderActionsMenu';

interface SearchFormInputs {
  query: string;
}

const themeOptions: { value: Theme; label: string; icon: typeof Monitor }[] = [
  { value: 'system', label: 'System Default', icon: Monitor },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
];

interface HeaderSearchFormProps {
  form: UseFormReturn<SearchFormInputs>;
  onSubmit: (data: SearchFormInputs) => void;
  placeholder: string;
  className?: string;
  inputClassName?: string;
}

function HeaderSearchForm({
  form,
  onSubmit,
  placeholder,
  className,
  inputClassName = '',
}: HeaderSearchFormProps) {
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className={className}>
        <FormField
          control={form.control}
          name="query"
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <div className="group/search relative">
                  <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 transition-colors group-focus-within/search:text-slate-700 dark:text-muted-foreground dark:group-focus-within/search:text-foreground" />
                  <input
                    type="text"
                    aria-label="Search AI Signal"
                    placeholder={placeholder}
                    className={`h-11 w-full rounded-full border border-slate-200/90 bg-white pl-11 pr-4 text-sm text-slate-950 shadow-[0_1px_2px_rgba(15,23,42,0.03),inset_0_1px_0_rgba(255,255,255,0.9)] outline-none transition-all placeholder:text-slate-400 hover:border-slate-300 hover:shadow-[0_3px_12px_rgba(15,23,42,0.05)] focus:border-slate-400 focus:ring-4 focus:ring-stone-950/[0.04] dark:border-border dark:bg-muted/45 dark:text-foreground dark:shadow-none dark:placeholder:text-muted-foreground dark:hover:border-foreground/18 dark:focus:border-ring/50 dark:focus:ring-ring/15 ${inputClassName}`}
                    {...field}
                  />
                </div>
              </FormControl>
            </FormItem>
          )}
        />
      </form>
    </Form>
  );
}

function LoggedOutAppearanceMenu() {
  const { setTheme, theme } = useTheme();
  const currentTheme = themeOptions.find((option) => option.value === theme);
  const CurrentThemeIcon = currentTheme?.icon ?? Monitor;

  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Change appearance"
          className="inline-flex h-10 w-10 items-center justify-center rounded-full text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 dark:text-muted-foreground dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
        >
          <CurrentThemeIcon className="h-5 w-5 stroke-[1.7]" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        sideOffset={10}
        className="w-52 rounded-lg border-slate-200/80 bg-white p-2 shadow-[0_18px_45px_rgba(15,23,42,0.12),0_2px_8px_rgba(15,23,42,0.06)] dark:border-border dark:bg-popover dark:shadow-[0_18px_45px_rgba(0,0,0,0.28),0_2px_8px_rgba(0,0,0,0.22)]"
      >
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
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const Header = () => {
  const navigate = useNavigate();
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

  const { user } = useAuth();

  const searchForm = useForm<SearchFormInputs>({
    defaultValues: {
      query: '',
    },
  });
  const mobileSearchForm = useForm<SearchFormInputs>({
    defaultValues: {
      query: '',
    },
  });

  const onSubmit = (data: SearchFormInputs) => {
    if (data.query.trim()) {
      navigate({ to: '/search-feed/$q', params: { q: data.query.trim() } });
      setMobileSearchOpen(false);
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200/80 bg-white/95 shadow-[0_1px_0_rgba(15,23,42,0.02)] backdrop-blur dark:border-border dark:bg-background/92 dark:shadow-none">
      <PageContainer
        variant="shell"
        spacing="none"
        gutters
        className="grid h-16 grid-cols-[1fr_auto] items-center gap-4 sm:h-[72px] md:grid-cols-[minmax(10rem,1fr)_minmax(22rem,40rem)_minmax(10rem,1fr)]"
      >
        <div className="flex min-w-0 items-center justify-start">
          <Link
            to="/"
            aria-label="AI Signal home"
            className="inline-flex min-w-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-4 dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            <span className="truncate font-display text-2xl font-semibold tracking-normal text-slate-950 sm:text-[1.7rem] dark:text-foreground">
              AI Signal
            </span>
          </Link>
        </div>

        <div className="hidden min-w-0 md:block">
          <HeaderSearchForm
            form={searchForm}
            onSubmit={onSubmit}
            placeholder="Search AI research, labs, topics..."
          />
        </div>

        <div className="flex items-center justify-end gap-2 sm:gap-4">
          <Link
            to="/all-article-sources"
            aria-label="Sources"
            className="hidden h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 md:inline-flex lg:hidden dark:border-border dark:bg-muted/45 dark:text-muted-foreground dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            <Library className="h-5 w-5 stroke-[1.7]" />
          </Link>
          <Sheet open={mobileSearchOpen} onOpenChange={setMobileSearchOpen}>
            <SheetTrigger asChild>
              <button
                type="button"
                aria-label="Search"
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 md:hidden dark:border-border dark:bg-muted/45 dark:text-muted-foreground dark:hover:border-foreground/18 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
              >
                <SearchIcon className="h-5 w-5 stroke-[1.7]" />
              </button>
            </SheetTrigger>
            <SheetContent
              side="top"
              className="border-b border-slate-200 bg-white px-4 pb-5 pt-4 shadow-[0_18px_45px_rgba(15,23,42,0.12)] dark:border-border dark:bg-background dark:shadow-[0_18px_45px_rgba(0,0,0,0.28)]"
            >
              <SheetHeader className="px-0 pb-3 pt-0">
                <SheetTitle className="text-left font-display text-xl font-semibold text-slate-950 dark:text-foreground">
                  Search AI Signal
                </SheetTitle>
              </SheetHeader>
              <HeaderSearchForm
                form={mobileSearchForm}
                onSubmit={onSubmit}
                placeholder="Search articles, labs, topics..."
                inputClassName="h-12 text-base"
              />
            </SheetContent>
          </Sheet>
          <Link
            to="/all-article-sources"
            className="hidden h-10 items-center gap-2 rounded-full px-2.5 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 lg:inline-flex dark:text-foreground/78 dark:hover:bg-accent dark:hover:text-foreground dark:focus-visible:ring-ring/35 dark:focus-visible:ring-offset-background"
          >
            <Library className="h-4 w-4 stroke-[1.7]" />
            Sources
          </Link>
          {user ? (
            <>
              <span
                aria-hidden="true"
                className="hidden h-6 w-px bg-slate-200/80 sm:block dark:bg-border"
              />
              <HeaderActionsMenu />
            </>
          ) : (
            <>
              <LoggedOutAppearanceMenu />
              <AuthModal />
            </>
          )}
        </div>
      </PageContainer>
    </header>
  );
};

export default Header;
