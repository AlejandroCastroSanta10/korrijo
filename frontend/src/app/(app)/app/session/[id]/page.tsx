"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Loader2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import ExamUpload from "@/components/sessions/exam-upload";
import ExamList from "@/components/sessions/exam-list";
import ExamResultDialog from "@/components/sessions/exam-result-dialog";
import { ApiError } from "@/lib/api";
import { useSession } from "@/lib/hooks/sessions";

type ResultView = "feedback" | "rubric";

function Stat({
  value,
  label,
  tone = "default",
}: {
  value: string | number;
  label: string;
  tone?: "default" | "passed" | "failed";
}) {
  const valueColor =
    tone === "passed"
      ? "text-emerald-600 dark:text-emerald-500"
      : tone === "failed"
        ? "text-destructive"
        : "text-foreground";
  return (
    <div className="flex flex-col items-center gap-1 rounded-2xl border border-input bg-input/20 px-4 py-5 text-center">
      <span className={`text-3xl font-bold ${valueColor}`}>{value}</span>
      <span className="text-sm text-muted-foreground">{label}</span>
    </div>
  );
}

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const { data: session, isLoading, isError, error } = useSession(id);
  const [openResult, setOpenResult] = useState<{
    examId: string;
    view: ResultView;
  } | null>(null);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center py-24">
        <Loader2 className="size-10 animate-spin text-primary" />
      </div>
    );
  }

  if (isError || !session) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 py-24 text-center">
        <TriangleAlert className="size-10 text-destructive" />
        <p className="font-semibold text-foreground">
          {notFound
            ? "No encontramos esta sesión"
            : "No se pudo cargar la sesión"}
        </p>
        <Button asChild variant="outline">
          <Link href="/app/new">Volver al inicio</Link>
        </Button>
      </div>
    );
  }

  const avg =
    session.average_score != null
      ? `${session.average_score.toLocaleString("es", {
          maximumFractionDigits: 2,
        })} / ${session.max_score.toLocaleString("es")}`
      : "—";

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-12">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold text-foreground sm:text-4xl">
          {session.name}
        </h1>
        <p className="text-base text-muted-foreground">
          Sube los exámenes que quieras que se corrijan y consulta los resultados propuestos.
        </p>
      </div>

      {/* Dashboard de métricas */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat value={session.graded_count} label="Exámenes corregidos" />
        <Stat value={session.passed_count} label="Aprobados" tone="passed" />
        <Stat value={session.failed_count} label="Suspensos" tone="failed" />
        <Stat value={avg} label="Nota media" />
      </div>

      {session.status !== "ready" && (
        <p className="flex items-start gap-2 rounded-xl bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>
            Esta sesión todavía no está lista para corregir exámenes.
          </span>
        </p>
      )}

      {session.status === "ready" && (
        <ExamUpload sessionId={session.id} />
      )}

      <ExamList
        exams={session.exams}
        maxScore={session.max_score}
        onOpenResult={(examId, view) => setOpenResult({ examId, view })}
      />

      <ExamResultDialog
        sessionId={session.id}
        examId={openResult?.examId ?? null}
        view={openResult?.view ?? "feedback"}
        maxScore={session.max_score}
        onClose={() => setOpenResult(null)}
      />
    </section>
  );
}
