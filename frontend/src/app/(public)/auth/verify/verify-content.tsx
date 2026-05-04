"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useVerifyMagicLink } from "@/lib/hooks/auth";
import { ApiError } from "@/lib/api";
import { toast } from "sonner";

function getErrorMessage(error: Error): string {
  if (error instanceof ApiError) {
    switch (error.message) {
      case "expired":
        return "El enlace ha caducado.";
      case "already_used":
        return "El enlace ya ha sido utilizado.";
      case "invalid":
        return "El enlace no es válido.";
      default:
        return "Ha ocurrido un error inesperado.";
    }
  }
  return "No se puede conectar con el servidor. Inténtalo más tarde.";
}

export function VerifyContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const router = useRouter();
  const { mutate, ...mutation } = useVerifyMagicLink();
  const hasVerified = useRef(false);

  useEffect(() => {
    if (!token || hasVerified.current) return;
    hasVerified.current = true;
    mutate(token, {
      onSuccess: () => {
        toast.success("Sesión iniciada correctamente");
        router.replace("/app/new");
      },
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  }, [token, mutate, router]);

  if (!token) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          No se ha proporcionado ningún token de acceso.
        </p>
        <Button asChild variant="outline">
          <Link href="/login">Ir al inicio de sesión</Link>
        </Button>
      </div>
    );
  }

  if (mutation.isPending || mutation.isIdle) {
    return (
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        Verificando...
      </p>
    );
  }

  if (mutation.isError) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <p className="font-semibold text-zinc-900 dark:text-zinc-50">
          No hemos podido iniciar tu sesión
        </p>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          {getErrorMessage(mutation.error)}
        </p>
        <Button asChild>
          <Link href="/login">Solicitar nuevo enlace</Link>
        </Button>
      </div>
    );
  }

  return null;
}
