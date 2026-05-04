"use client";

import { useCurrentUser } from "@/lib/hooks/auth";

// Será la página de creación de una sesión de corrección
export default function NewPage() {
  const { data: user } = useCurrentUser();

  return (
    <section className="flex flex-1 flex-col gap-4 px-6 py-16 max-w-7xl mx-auto w-full">
      <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
        Bienvenido a la parte privada de Korrijo
        {user?.email ? `, ${user.email}` : ""}
      </h1>
      <p className="text-zinc-500 dark:text-zinc-400">
        Esta área se irá completando en próximas versiones.
      </p>
    </section>
  );
}
