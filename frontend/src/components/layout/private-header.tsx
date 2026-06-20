"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { CircleHelp, CircleUser, Globe, History, Plus, Settings } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCurrentUser, useLogout } from "@/lib/hooks/auth";

export default function PrivateHeader() {
  const router = useRouter();
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSuccess: () => {
        router.replace("/login");
      },
      onError: () => {
        toast.error("No se pudo cerrar la sesión. Inténtalo de nuevo.");
      },
    });
  };

  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link
          href="/app/new"
          className="flex items-center gap-2 font-bold text-zinc-900 dark:text-zinc-50"
        >
          <i className="text-3xl">Korrijo</i>
        </Link>

        <nav className="hidden items-center gap-15 sm:flex">
          <Link
            href="/app/new"
            className="flex items-center gap-2 text-lg font-medium text-zinc-900 underline-offset-8 hover:underline dark:text-zinc-50"
          >
            <Plus className="size-5" />
            Nueva sesión de corrección
          </Link>
          <Link
            href="/app/history"
            className="flex items-center gap-2 text-lg font-medium text-zinc-900 underline-offset-8 hover:underline dark:text-zinc-50"
          >
            <History className="size-5" />
            Historial de sesiones
          </Link>
        </nav>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Menú de usuario">
              <CircleUser className="size-8" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel className="flex flex-col gap-0.5">
              {user?.name && (
                <span className="font-medium text-xl text-foreground">{user.name}</span>
              )}
              <span className="font-normal text-base">
                {user?.email ?? "—"}
              </span>
            </DropdownMenuLabel>

            <DropdownMenuSeparator />

            <DropdownMenuItem asChild>
              <Link href="/app/settings">
                <Settings className="size-4" />
                Configuración
              </Link>
            </DropdownMenuItem>

            <DropdownMenuItem asChild>
              <Link href="/contact">
                <CircleHelp className="size-4" />
                Ayuda
              </Link>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              onClick={handleLogout}
              disabled={logout.isPending}
              className="text-red-600 focus:text-red-600 dark:text-red-400 dark:focus:text-red-400"
            >
              {logout.isPending ? "Cerrando sesión..." : "Cerrar sesión"}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
