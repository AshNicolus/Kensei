import { LogOut, User } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu";
import { useAuth } from "@/shared/hooks/use-auth";
import { tokenStore } from "@/shared/lib/api";

export function Topbar() {
  const { user, logout } = useAuth();
  const email = user?.email ?? tokenStore.getEmail() ?? "";
  const initial = (email[0] || "?").toUpperCase();

  return (
    <header className="h-14 border-b border-border/60 px-6 flex items-center justify-between gap-4 bg-background/40 backdrop-blur sticky top-0 z-20">
      <div className="text-sm text-muted-foreground hidden md:block">
        <span className="font-mono text-xs">v0.1.0 · private beta</span>
      </div>
      <div className="md:hidden font-semibold">Kensei</div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="gap-2 px-2">
            <span className="size-6 rounded-full bg-primary/20 text-primary grid place-items-center text-xs font-medium">
              {initial}
            </span>
            <span className="hidden sm:inline text-sm font-normal">{email}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="flex flex-col gap-0.5">
            <span className="text-xs text-muted-foreground">Signed in as</span>
            <span className="text-sm text-foreground font-normal truncate">
              {email}
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem disabled>
            <User className="size-4" />
            Account settings
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={logout}>
            <LogOut className="size-4" />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
