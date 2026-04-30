// Este es un server component

import { BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

const navLinks = [
  { label: "Sobre la herramienta", href: "/login#about" },
  { label: "FAQs", href: "/login#faqs" },
  { label: "Ayuda", href: "/contact" },
];

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <a
          href="/login#auth"
          className="flex items-center gap-2 font-bold text-zinc-900 dark:text-zinc-50"
        >
          <BookOpen className="size-5" />
          Korrijo
        </a>

        <nav className="hidden items-center gap-6 text-sm text-zinc-600 sm:flex dark:text-zinc-400">
          {navLinks.map(({ label, href }) => (
            <a
              key={href}
              href={href}
              className="transition-colors hover:text-zinc-900 dark:hover:text-zinc-50"
            >
              {label}
            </a>
          ))}
        </nav>

        <Button asChild>
          <a href="/login#auth">¡Prueba Korrijo ahora!</a>
        </Button>
      </div>
    </header>
  );
}
