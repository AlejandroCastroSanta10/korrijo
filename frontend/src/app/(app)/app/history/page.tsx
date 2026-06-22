"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, FolderOpen, Loader2, Plus, Trash2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  MAX_ACTIVE_SESSIONS,
  useDeleteSession,
  useSessions,
  type SessionRead,
} from "@/lib/hooks/sessions";

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

function SessionCard({
  session,
  onDelete,
}: {
  session: SessionRead;
  onDelete: (session: SessionRead) => void;
}) {
  const avg =
    session.average_score != null
      ? ` · Nota media de la sesión: ${session.average_score.toLocaleString("es", {
          maximumFractionDigits: 2,
        })}`
      : "";

  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-input bg-card px-7 py-6">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="truncate text-xl font-semibold text-foreground">
          {session.name}
        </span>
        <span className="text-base">
          Creada el {formatDate(session.created_at)} · {session.graded_count}{" "}
          {session.graded_count === 1 ? "examen corregido" : "exámenes corregidos"}
          {avg}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Button asChild variant="outline" size="lg" className="text-base">
          <Link href={`/app/session/${session.id}`}>
            Abrir
            <ArrowRight className="size-5" />
          </Link>
        </Button>
        <Button
          variant="ghost"
          size="icon-lg"
          aria-label={`Borrar la sesión ${session.name}`}
          className="text-muted-foreground hover:text-destructive"
          onClick={() => onDelete(session)}
        >
          <Trash2 className="size-6" />
        </Button>
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const { data: sessions, isLoading, isError } = useSessions();
  const deleteSession = useDeleteSession();
  const [toDelete, setToDelete] = useState<SessionRead | null>(null);

  const handleConfirmDelete = () => {
    if (!toDelete) return;
    deleteSession.mutate(toDelete.id, {
      onSuccess: () => {
        toast.success("Sesión borrada.");
        setToDelete(null);
      },
      onError: () => {
        toast.error("No se pudo borrar la sesión. Inténtalo de nuevo.");
      },
    });
  };

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-12">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold text-foreground sm:text-4xl">
          Historial de sesiones de corrección
        </h1>
      </div>

      {isLoading && (
        <div className="flex flex-1 items-center justify-center py-24">
          <Loader2 className="size-10 animate-spin text-primary" />
        </div>
      )}

      {isError && (
        <p className="flex items-center gap-2 py-8 text-sm text-destructive">
          <TriangleAlert className="size-4" />
          No se pudo cargar el historial de sesiones.
        </p>
      )}

      {sessions && sessions.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center gap-6 py-24 text-center">
          <FolderOpen className="size-20 text-muted-foreground/40" strokeWidth={1.5} />
          <div className="flex flex-col gap-3">
            <h2 className="text-3xl font-bold text-foreground">
              Aún no tienes ninguna sesión de corrección
            </h2>
            <p className="max-w-xl text-lg">
              ¡Crea tu primera sesión y empieza a corregir exámenes con <i>Korrijo</i>!
            </p>
          </div>
          <Button asChild size="lg" className="mt-2 text-base">
            <Link href="/app/new">
              <Plus className="size-5" />
              Crear sesión de corrección
            </Link>
          </Button>
        </div>
      )}

      {sessions && sessions.length > 0 && (
        <div className="flex flex-col gap-3 mt-2">
          {sessions.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              onDelete={setToDelete}
            />
          ))}
        </div>
      )}

      {sessions && sessions.length > 0 && (
        <i className="text-base text-lg mt-4">
          Tienes {sessions.length}{" "}
          {sessions.length === 1 ? "sesión activa" : "sesiones activas"} de un
          máximo de {MAX_ACTIVE_SESSIONS} posibles.
        </i>
      )}

      <Dialog
        open={!!toDelete}
        onOpenChange={(open) => !open && setToDelete(null)}
      >
        <DialogContent className="gap-6 p-8 sm:max-w-2xl">
          <DialogHeader className="gap-3">
            <DialogTitle className="text-3xl">¿Estás seguro/a?</DialogTitle>
            <DialogDescription className="text-lg leading-relaxed mt-2">
              Al borrar la sesión <b>{toDelete?.name}</b> se eliminarán todos sus datos
              (exámenes, informes, calificaciones propuestas, etc.) del sistema. Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              size="lg"
              variant="outline"
              className="text-base"
              onClick={() => setToDelete(null)}
              disabled={deleteSession.isPending}
            >
              Cancelar
            </Button>
            <Button
              size="lg"
              variant="destructive"
              className="text-base"
              onClick={handleConfirmDelete}
              disabled={deleteSession.isPending}
            >
              {deleteSession.isPending ? (
                <Loader2 className="size-5 animate-spin" />
              ) : (
                <Trash2 className="size-5" />
              )}
              Borrar sesión
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}
