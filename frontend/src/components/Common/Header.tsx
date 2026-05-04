import { Link, useNavigate } from "@tanstack/react-router"
import { SearchIcon } from "lucide-react"
import { useForm } from "react-hook-form"
import useAuth from "@/hooks/useAuth"
import AuthModal from "../Auth/AuthModal"
import { Form, FormControl, FormField, FormItem } from "../ui/form"
import { HeaderActionsMenu } from "./HeaderActionsMenu"

interface SearchFormInputs {
  query: string
}

const Header = () => {
  const navigate = useNavigate()

  const { user } = useAuth()

  const searchForm = useForm<SearchFormInputs>({
    defaultValues: {
      query: "",
    },
  })

  const onSubmit = (data: SearchFormInputs) => {
    if (data.query.trim()) {
      navigate({ to: "/search-feed/$q", params: { q: data.query.trim() } })
    }
  }

  return (
    <header className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="mx-auto h-20 flex items-center justify-between px-10 sm:px-12 md:px-14 lg:px-16">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 group">
            <span className="font-serif font-semibold text-3xl tracking-tight">
              AI Signal
            </span>
          </Link>

          <div className="relative hidden sm:block">
            <Form {...searchForm}>
              <form onSubmit={searchForm.handleSubmit(onSubmit)}>
                <FormField
                  control={searchForm.control}
                  name="query"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <div className="relative">
                          <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-slate-400 stroke-[1.5]" />
                          <input
                            type="text"
                            placeholder="Search..."
                            className="h-10 w-60 rounded-full bg-slate-50 border-transparent focus:bg-white focus:border-slate-200 pl-9 pr-4 text-sm outline-none transition-all placeholder:text-slate-400"
                            {...field}
                          />
                        </div>
                      </FormControl>
                    </FormItem>
                  )}
                />
              </form>
            </Form>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {user ? <HeaderActionsMenu /> : <AuthModal />}
        </div>
      </div>
    </header>
  )
}

export default Header
