"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { CircleUser, History, Plus, Settings } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCurrentUser, useLogout } from "@/lib/hooks/auth";

const appLinks = [
  { label: "Sobre el creador", href: "/creator" },
  { label: "Términos y políticas", href: "/politics" },
  { label: "Contacto", href: "/contact" },
];

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

        <nav className="hidden items-center gap-6 sm:flex">
          <Link
            href="/app/new"
            className="flex items-center gap-2 text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
          >
            <Plus className="size-5" />
            Nueva sesión de corrección
          </Link>
          <Link
            href="/app/history"
            className="flex items-center gap-2 text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
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

          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal text-zinc-500 dark:text-zinc-400">
              {user?.name ?? (user?.email ?? "—")}
            </DropdownMenuLabel>

            <DropdownMenuSeparator />

            <DropdownMenuItem asChild>
              <Link href="/app/settings">
                <Settings className="size-4" />
                Configuración
              </Link>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            {appLinks.map(({ label, href }) => (
              <DropdownMenuItem key={href} asChild>
                <Link href={href}>{label}</Link>
              </DropdownMenuItem>
            ))}

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
