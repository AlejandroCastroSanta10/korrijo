import Link from "next/link";
import { BookOpen } from "lucide-react";

const footerLinks = [
  { label: "Términos y políticas", href: "/politics" },
  { label: "Sobre mí", href: "/creator" },
  { label: "Contacto", href: "/contact" },
];

export default function Footer() {
  return (
    <footer className="border-t border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 px-6 py-10 sm:flex-row sm:justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 font-bold text-zinc-900 dark:text-zinc-50"
        >
          <BookOpen className="size-5" />
          Korrijo
        </Link>

        <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-zinc-500 dark:text-zinc-400">
          {footerLinks.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className="transition-colors hover:text-zinc-900 dark:hover:text-zinc-50"
            >
              {label}
            </Link>
          ))}
        </nav>

        <p className="text-sm text-zinc-400 dark:text-zinc-500">
          © 2026 Alejandro Castro Santa
        </p>
      </div>
    </footer>
  );
}
