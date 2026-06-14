import Link from "next/link";

const footerLinks = [
  { label: "Términos y políticas", href: "/politics" },
  { label: "Sobre el creador", href: "/creator" },
  { label: "Contacto", href: "/contact" },
];

export default function Footer({ homeHref = "/login" }: { homeHref?: string }) {
  return (
    <footer className="border-t border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex w-full flex-col items-center gap-4 px-8 py-10 sm:grid sm:grid-cols-3 sm:items-center">
        <Link
          href={homeHref}
          className="flex items-center gap-2 font-bold text-zinc-900 dark:text-zinc-50 sm:justify-self-start"
        >
          <i className="text-xl">Korrijo</i>
        </Link>

        <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-zinc-500 dark:text-zinc-400 sm:justify-self-center">
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

        <p className="dark:text-zinc-500 sm:justify-self-end">
          © 2026 Alejandro Castro Santa
        </p>
      </div>
    </footer>
  );
}
