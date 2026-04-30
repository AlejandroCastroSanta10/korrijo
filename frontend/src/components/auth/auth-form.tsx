"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4 shrink-0">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}

export default function AuthForm() {
  const [email, setEmail] = useState("");

  return (
    <div className="flex flex-col gap-6">
      <p className="text-center text-zinc-600 dark:text-zinc-400">
        Inicia sesión o regístrate en el sistema para usar la herramienta
      </p>

      <div className="flex flex-col gap-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        {/* TODO: Google OAuth en v0.2.0 */}
        <Button variant="outline" className="w-full gap-2">
          <GoogleIcon />
          Continúa con Google
        </Button>

        <div className="flex items-center gap-3">
          <Separator className="flex-1" />
          <span className="text-sm text-zinc-400">o</span>
          <Separator className="flex-1" />
        </div>

        <div className="flex flex-col gap-2">
          <Input
            type="email"
            placeholder="Introduce tu correo electrónico"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          {/* TODO: magic link en v0.2.0 */}
          <Button className="w-full" disabled={!email}>
            Continuar con email
          </Button>
        </div>

        <p className="text-center text-xs text-zinc-400">
          Al continuar, reconoces las{" "}
          <Link href="/politics" className="underline hover:text-zinc-700 dark:hover:text-zinc-200">
            políticas de Korrijo
          </Link>
        </p>
      </div>
    </div>
  );
}
