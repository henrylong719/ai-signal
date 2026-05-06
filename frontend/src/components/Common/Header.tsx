import { Link, useNavigate } from "@tanstack/react-router"
import { SearchIcon } from "lucide-react"
import { useState } from "react"
import { type UseFormReturn, useForm } from "react-hook-form"
import useAuth from "@/hooks/useAuth"
import AuthModal from "../Auth/AuthModal"
import { Form, FormControl, FormField, FormItem } from "../ui/form"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "../ui/sheet"
import { HeaderActionsMenu } from "./HeaderActionsMenu"

interface SearchFormInputs {
  query: string
}

interface HeaderSearchFormProps {
  form: UseFormReturn<SearchFormInputs>
  onSubmit: (data: SearchFormInputs) => void
  placeholder: string
  className?: string
  inputClassName?: string
}

function HeaderSearchForm({
  form,
  onSubmit,
  placeholder,
  className,
  inputClassName = "",
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
                  <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 transition-colors group-focus-within/search:text-slate-700" />
                  <input
                    type="text"
                    aria-label="Search AI Signal"
                    placeholder={placeholder}
                    className={`h-11 w-full rounded-full border border-slate-200/90 bg-white pl-11 pr-4 text-sm text-slate-950 shadow-[0_1px_2px_rgba(15,23,42,0.03),inset_0_1px_0_rgba(255,255,255,0.9)] outline-none transition-all placeholder:text-slate-400 hover:border-slate-300 hover:shadow-[0_3px_12px_rgba(15,23,42,0.05)] focus:border-slate-400 focus:ring-4 focus:ring-cyan-950/[0.04] ${inputClassName}`}
                    {...field}
                  />
                </div>
              </FormControl>
            </FormItem>
          )}
        />
      </form>
    </Form>
  )
}

const Header = () => {
  const navigate = useNavigate()
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false)

  const { user } = useAuth()

  const searchForm = useForm<SearchFormInputs>({
    defaultValues: {
      query: "",
    },
  })
  const mobileSearchForm = useForm<SearchFormInputs>({
    defaultValues: {
      query: "",
    },
  })

  const onSubmit = (data: SearchFormInputs) => {
    if (data.query.trim()) {
      navigate({ to: "/search-feed/$q", params: { q: data.query.trim() } })
      setMobileSearchOpen(false)
    }
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200/80 bg-white/95 shadow-[0_1px_0_rgba(15,23,42,0.02)] backdrop-blur">
      <div className="mx-auto grid h-16 w-full max-w-[1480px] grid-cols-[1fr_auto] items-center gap-4 px-4 sm:h-[72px] sm:px-6 md:grid-cols-[minmax(10rem,1fr)_minmax(22rem,40rem)_minmax(10rem,1fr)] lg:px-8">
        <div className="flex min-w-0 items-center justify-start">
          <Link
            to="/"
            aria-label="AI Signal home"
            className="inline-flex min-w-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-4"
          >
            <span className="truncate font-display text-2xl font-semibold text-slate-950 sm:text-[1.7rem]">
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
          <Sheet open={mobileSearchOpen} onOpenChange={setMobileSearchOpen}>
            <SheetTrigger asChild>
              <button
                type="button"
                aria-label="Search"
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950/15 focus-visible:ring-offset-2 md:hidden"
              >
                <SearchIcon className="h-5 w-5 stroke-[1.7]" />
              </button>
            </SheetTrigger>
            <SheetContent
              side="top"
              className="border-b border-slate-200 bg-white px-4 pb-5 pt-4 shadow-[0_18px_45px_rgba(15,23,42,0.12)]"
            >
              <SheetHeader className="px-0 pb-3 pt-0">
                <SheetTitle className="text-left font-display text-xl font-semibold text-slate-950">
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
          <span
            aria-hidden="true"
            className="hidden h-6 w-px bg-slate-200/80 sm:block"
          />
          {user ? <HeaderActionsMenu /> : <AuthModal />}
        </div>
      </div>
    </header>
  )
}

export default Header
