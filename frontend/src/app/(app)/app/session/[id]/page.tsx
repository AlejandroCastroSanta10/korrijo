"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, FileQuestion, Loader2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import ExamUpload from "@/components/sessions/exam-upload";
import ExamList from "@/components/sessions/exam-list";
import ExamResultDialog from "@/components/sessions/exam-result-dialog";
import InfoHint from "@/components/sessions/info-hint";
import { ApiError } from "@/lib/api";
import { isExamActive, useSession } from "@/lib/hooks/sessions";

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
      ? "text-green-600 dark:text-green-500"
      : tone === "failed"
        ? "text-destructive"
        : "text-foreground";
  return (
    <div className="flex flex-1 flex-col items-center gap-2 px-6 py-8 text-center sm:py-10">
      <span className={`font-bold sm:text-4xl ${valueColor}`}>
        {value}
      </span>
      <span className="text-base text-foreground sm:text-lg">{label}</span>
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
    const Icon = notFound ? FileQuestion : TriangleAlert;
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-24 text-center">
        <Icon
          className={`size-20 ${
            notFound ? "text-muted-foreground/40" : "text-destructive/70"
          }`}
          strokeWidth={1.5}
        />
        <div className="flex flex-col gap-3">
          <h2 className="text-3xl text-foreground">
            {notFound
              ? "No encontramos esta sesión"
              : "No se pudo cargar la sesión"}
          </h2>
          <p className="max-w-xl text-lg">
            {notFound
              ? "Puede que se haya borrado o que el enlace no sea correcto."
              : "Ha ocurrido un problema al cargar esta sesión de corrección. Vuelve a intentarlo en unos instantes."}
          </p>
        </div>
        <Button asChild size="lg" className="mt-2 text-base">
          <Link href="/app/new">
            <ArrowLeft className="size-5" />
            Volver al inicio
          </Link>
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
        <p className="text-lg mt-4">
          Sube los exámenes que quieras que se corrijan automáticamente. Por cada correción llevada a cabo con éxito <i>Korrijo</i> genera 
          una calificación orientativa propuesta, la rúbrica rellenada y un informe con <i>feedback</i> general para el profesor.
        </p>
      </div>

      {/* Dashboard de métricas */}
      <div className="mt-4 flex flex-col divide-y divide-input rounded-2xl border border-input bg-card shadow-sm sm:flex-row sm:divide-x sm:divide-y-0">
        <Stat value={session.graded_count} label="Exámenes corregidos" />
        <Stat value={session.passed_count} label="Aprobados" tone="passed" />
        <Stat value={session.failed_count} label="Suspensos" tone="failed" />
        <Stat
          value={avg}
          label="Nota media"
          tone={
            session.average_score == null
              ? "default"
              : session.average_score >= session.max_score / 2
                ? "passed"
                : "failed"
          }
        />
      </div>

      {session.status !== "ready" && (
        <p className="flex items-start gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-base text-amber-700 dark:text-amber-400">
          <TriangleAlert className="mt-0.5 size-5 shrink-0" />
          <span>
            Esta sesión todavía no está lista para corregir exámenes.
          </span>
        </p>
      )}

      {session.status === "ready" && (
        <div className="flex flex-col gap-3 mt-4">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl text-foreground">
              Zona de subida de instancias de examen:
            </h2>
            <InfoHint text="Sube aquí las pruebas evaluativas manuscritas que quieras que se corrijan automáticamente. Cada uno escaneado en .pdf o UNA ÚNICA imagen (.jpg, .png o .jpeg). Hasta 5 MB por examen. 
            Máximo introducir 3 a la vez en este campo. No puede haber más de 2 esperando a ser procesados." />
          </div>
          <ExamUpload
            sessionId={session.id}
            activeExamCount={
              session.exams.filter((e) => isExamActive(e.status)).length
            }
          />
        </div>
      )}

      <div className="flex items-center gap-2 mt-6">
        <h2 className="text-2xl text-foreground">
          Listado de pruebas evaluativas procesadas:
        </h2>
        <InfoHint text="Aquí aparecen los exámenes subidos junto con su estado de procesamiento. De cada examen corregido puedes ver la calificación propuesta y 
        ver y descargar la rúbrica rellenada y el informe con la retroalimentación general." />
      </div>
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
