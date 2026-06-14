// Este es un server component

import { Button } from "@/components/ui/button";

const navLinks = [
  { label: "Sobre la herramienta", href: "/login#about" },
  { label: "FAQs", href: "/login#faqs" },
  { label: "Ayuda", href: "/contact" },
];

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="mx-auto flex h-20 max-w-5xl items-center justify-between px-6">
        <a
          href="/login#auth"
          className="flex items-center gap-2 font-bold text-zinc-900 dark:text-zinc-50"
        >
          <i className="text-4xl">Korrijo</i>
        </a>

        <nav className="hidden items-center gap-8 text-lg font-medium text-foreground/80 sm:flex">
          {navLinks.map(({ label, href }) => (
            <a
              key={href}
              href={href}
              className="transition-colors hover:text-foreground"
            >
              {label}
            </a>
          ))}
        </nav>

        <Button asChild size="lg" className="text-base">
          <a href="/login#auth">¡Prueba Korrijo ahora!</a>
        </Button>
      </div>
    </header>
  );
}
