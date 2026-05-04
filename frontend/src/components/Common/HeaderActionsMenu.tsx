import { Link as RouterLink } from "@tanstack/react-router"
import { Bookmark, LogOut } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/useAuth"
import { getInitials } from "@/utils"
import { Avatar, AvatarFallback } from "../ui/avatar"

interface UserInfoProps {
  fullName?: string
  email?: string
}

function UserInfo({ fullName, email }: UserInfoProps) {
  return (
    <div className="flex items-center gap-2.5 w-full min-w-0">
      <Avatar className="size-8">
        <AvatarFallback className="bg-zinc-600 text-white">
          {getInitials(fullName || "User")}
        </AvatarFallback>
      </Avatar>
      <div className="flex flex-col items-start min-w-0">
        <p className="text-sm font-medium truncate w-full">{fullName}</p>
        <p className="text-xs text-muted-foreground truncate w-full">{email}</p>
      </div>
    </div>
  )
}

export const HeaderActionsMenu = () => {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()

  const handleLogout = async () => {
    logout()
  }

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          {/* <UserCircle2Icon className="w-10 h-10 stroke-[1.5]" /> */}

          <Avatar className="bg-zinc-600 text-white">
            {getInitials(user?.full_name || "User")}
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
        side={"bottom"}
        align="end"
        sideOffset={4}
      >
        <RouterLink to="/settings">
          <DropdownMenuLabel className="py-4">
            <UserInfo fullName={user?.full_name || ""} email={user?.email} />
          </DropdownMenuLabel>
        </RouterLink>
        <DropdownMenuSeparator />
        <RouterLink to="/saved-articles">
          <DropdownMenuItem>
            <Bookmark />
            Your library
          </DropdownMenuItem>
        </RouterLink>
        <DropdownMenuItem onClick={handleLogout}>
          <LogOut />
          Log Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
