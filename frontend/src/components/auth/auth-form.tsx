"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRequestMagicLink } from "@/lib/hooks/auth";
import { ApiError } from "@/lib/api";
import { toast } from "sonner";
import { MailCheck } from "lucide-react";

const RESEND_COOLDOWN = 30;

const schema = z.object({
  email: z.email("Introduce un email válido."),
});
type FormData = z.infer<typeof schema>;

function getErrorMessage(error: Error): string {
  if (error instanceof ApiError) {
    if (error.status === 429) {
      return "Hemos enviado demasiadas solicitudes a ese email. Espera unos minutos para volver a hacerlo.";
    }
    return error.message;
  }
  return "No se puede conectar con el servidor. Inténtalo más tarde.";
}

function EmailForm({ onSuccess }: { onSuccess: (email: string) => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const mutation = useRequestMagicLink();

  // Enfocamos el campo del correo para invitar al usuario a introducirlo (cuando llegamoa a auth). 
  useEffect(() => {
    const focusEmail = () => {
      if (window.location.hash === "#auth") {
        document.getElementById("auth-email")?.focus();
      }
    };
    focusEmail();
    window.addEventListener("hashchange", focusEmail);
    return () => window.removeEventListener("hashchange", focusEmail);
  }, []);

  const onSubmit = (data: FormData) => {
    mutation.mutate(data.email, {
      onSuccess: () => onSuccess(data.email),
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-2">
      <Input
        id="auth-email"
        type="email"
        placeholder="Introduce tu correo electrónico"
        className="h-12 text-xl md:text-medium"
        aria-invalid={!!errors.email}
        {...register("email")}
      />
      {errors.email && (
        <p className="text-medium text-red-500">{errors.email.message}</p>
      )}
      {mutation.error && (
        <p className="text-medium text-red-500">{getErrorMessage(mutation.error)}</p>
      )}
      <Button
        type="submit"
        size="lg"
        className="w-full text-base mt-2"
        disabled={mutation.isPending}
      >
        {mutation.isPending ? "Cargando..." : "Continuar"}
      </Button>
    </form>
  );
}

function EmailSentView({
  email,
  onChangeEmail,
}: {
  email: string;
  onChangeEmail: () => void;
}) {
  const mutation = useRequestMagicLink();
  const [cooldown, setCooldown] = useState(RESEND_COOLDOWN);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleResend = () => {
    mutation.mutate(email, {
      onSuccess: () => {
        setCooldown(RESEND_COOLDOWN);
        toast.success("Enlace reenviado");
      },
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  return (
    <div className="flex flex-col items-center gap-5 text-center">
      <div className="flex size-14 items-center justify-center rounded-full bg-primary/10">
        <MailCheck className="size-7 text-primary" />
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
          Revisa tu correo
        </p>
        <p className="text-base text-zinc-700 dark:text-zinc-300">
          Hemos enviado un enlace de acceso a{" "}
          <span className="font-semibold text-primary">{email}</span>
        </p>
      </div>

      <Button
        variant="outline"
        size="lg"
        className="w-full text-base"
        disabled={cooldown > 0 || mutation.isPending}
        onClick={handleResend}
      >
        {mutation.isPending
          ? "Reenviando..."
          : cooldown > 0
            ? `Reenviar enlace (${cooldown}s)`
            : "Reenviar enlace"}
      </Button>

      <button
        type="button"
        onClick={onChangeEmail}
        className="text-sm text-zinc-600 underline hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
      >
        Cambiar de email
      </button>
    </div>
  );
}

export default function AuthForm() {
  const [view, setView] = useState<"form" | "sent">("form");
  const [submittedEmail, setSubmittedEmail] = useState("");

  const handleSuccess = (email: string) => {
    setSubmittedEmail(email);
    setView("sent");
  };

  return (
    <div className="flex w-full max-w-md flex-col gap-8">
      <p className="text-xl text-center text-zinc-700 dark:text-zinc-300">
        <b>Inicia sesión</b> o <b>regístrate</b> en el sistema para usar la herramienta
      </p>

      <div className="flex flex-col gap-5 rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        {view === "form" ? (
          <>
            <EmailForm onSuccess={handleSuccess} />
            <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
              Al continuar, reconoces las{" "}
              <Link
                href="/politics"
                className="underline hover:text-zinc-700 dark:hover:text-zinc-200"
              >
                políticas de <i>Korrijo</i>
              </Link>
            </p>
          </>
        ) : (
          <EmailSentView
            email={submittedEmail}
            onChangeEmail={() => setView("form")}
          />
        )}
      </div>
    </div>
  );
}
