// Este es un server component

import Link from "next/link";
import { BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

const navLinks = [
  { label: "Sobre la herramienta", href: "#about" },
  { label: "FAQs", href: "#faqs" },
  { label: "Ayuda", href: "/contacto" },
];

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <Link
          href="/"
          className="flex items-center gap-2 font-bold text-zinc-900 dark:text-zinc-50"
        >
          <BookOpen className="size-5" />
          Korrijo
        </Link>

        <nav className="hidden items-center gap-6 text-sm text-zinc-600 sm:flex dark:text-zinc-400">
          {navLinks.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className="transition-colors hover:text-zinc-900 dark:hover:text-zinc-50"
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* TODO: link a /login en v0.2.0 */}
        <Button>¡Prueba Korrijo ahora!</Button>
      </div>
    </header>
  );
}
