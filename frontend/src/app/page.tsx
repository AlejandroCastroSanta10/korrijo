"use client";

import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "@/lib/api";

type Status =
  | { kind: "loading" }
  | { kind: "success"; data: HealthResponse }
  | { kind: "error"; message: string };

export default function Home() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    fetchHealth()
      .then((data) => setStatus({ kind: "success", data }))
      .catch((err: unknown) =>
        setStatus({
          kind: "error",
          message: err instanceof Error ? err.message : "Error desconocido",
        }),
      );
  }, []);

  return (
    <html>
      <body>
        <div className="flex flex-1 items-center justify-center bg-zinc-50 dark:bg-black">
          <main className="flex flex-col items-center gap-4 rounded-2xl border border-zinc-200 bg-white p-10 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Estado del backend
            </h1>

            {status.kind === "loading" && (
              <p className="text-zinc-500">Comprobando conexión…</p>
            )}

            {status.kind === "success" && (
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <span className="text-lg">✓</span>
                <span className="font-mono text-sm">
                  {JSON.stringify(status.data)}
                </span>
              </div>
            )}

            {status.kind === "error" && (
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                <span className="text-lg">✗</span>
                <span className="text-sm">{status.message}</span>
              </div>
            )}
          </main>
        </div>
      </body>
    </html>
  );
}
