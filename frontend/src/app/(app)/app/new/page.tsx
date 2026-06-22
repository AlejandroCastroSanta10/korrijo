"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import NewSessionForm, {
  type NewSessionValues,
} from "@/components/sessions/new-session-form";
import RubricReview from "@/components/sessions/rubric-review";
import RecentSessionCard from "@/components/sessions/recent-session-card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import {
  useCreateSession,
  useUploadDocument,
  useValidateRubric,
  useSessions,
  MAX_ACTIVE_SESSIONS,
  type DocumentKind,
  type RubricItem,
} from "@/lib/hooks/sessions";

type Phase = "form" | "uploading" | "review";

interface UploadJob {
  kind: DocumentKind;
  file: File;
}

function messageFrom(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "No se pudo conectar con el servidor. Inténtalo de nuevo.";
}

function buildJobs(v: NewSessionValues): UploadJob[] {
  return [
    ...v.contextFiles.map((file) => ({ kind: "context" as const, file })),
    { kind: "model_exam" as const, file: v.modelFiles[0] },
    { kind: "rubric" as const, file: v.rubricFiles[0] },
  ];
}

function jobLabel(kind: DocumentKind): string {
  switch (kind) {
    case "context":
      return "Subiendo material de contexto...";
    case "model_exam":
      return "Subiendo el examen modelo...";
    case "rubric":
      return "Analizando con IA la rúbrica proporcionada (puede tardar un poco)...";
  }
}

export default function NewSessionPage() {
  const router = useRouter();
  const create = useCreateSession();
  const upload = useUploadDocument();
  const validate = useValidateRubric();
  const { data: sessions, isLoading: sessionsLoading } = useSessions();

  // El backend cuenta como activas las sesiones que no están archivadas.
  const activeCount =
    sessions?.filter((s) => s.status !== "archived").length ?? 0;
  const atLimit = activeCount >= MAX_ACTIVE_SESSIONS;

  const [phase, setPhase] = useState<Phase>("form");
  const [values, setValues] = useState<NewSessionValues | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const [doneCount, setDoneCount] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [rubricItems, setRubricItems] = useState<RubricItem[]>([]);
  const [rubricWarning, setRubricWarning] = useState<string | null>(null);

  // Crea la sesión (si no existe) y sube los documentos pendientes en orden.
  async function runFlow(
    vals: NewSessionValues,
    pending: UploadJob[],
    existingId: string | null,
    startIndex: number,
  ) {
    setUploadError(null);
    let id = existingId;
    try {
      if (!id) {
        const created = await create.mutateAsync({
          name: vals.name,
          max_score: vals.maxScore,
          context_instructions: vals.contextInstructions?.trim() || null,
          model_exam_instructions: vals.modelInstructions?.trim() || null,
        });
        id = created.id;
        setSessionId(id);
      }

      for (let i = startIndex; i < pending.length; i++) {
        const job = pending[i];
        const res = await upload.mutateAsync({
          sessionId: id,
          kind: job.kind,
          file: job.file,
        });
        setDoneCount(i + 1);
        if (job.kind === "rubric") {
          setRubricItems(res.rubric?.items ?? []);
          setRubricWarning(res.rubric?.warning ?? null);
        }
      }

      setPhase("review");
    } catch (err) {
      setUploadError(messageFrom(err));
    }
  }

  const handleFormSubmit = (vals: NewSessionValues) => {
    const pending = buildJobs(vals);
    setValues(vals);
    setJobs(pending);
    setDoneCount(0);
    setSessionId(null);
    setPhase("uploading");
    void runFlow(vals, pending, null, 0);
  };

  const handleRetry = () => {
    if (!values) return;
    void runFlow(values, jobs, sessionId, doneCount);
  };

  const handleStartOver = () => {
    setValues(null);
    setSessionId(null);
    setJobs([]);
    setDoneCount(0);
    setUploadError(null);
    setRubricItems([]);
    setRubricWarning(null);
    setPhase("form");
  };

  const handleConfirmRubric = (items: RubricItem[]) => {
    if (!sessionId) return;
    validate.mutate(
      { sessionId, items },
      {
        onSuccess: () => {
          toast.success("Sesión lista para corregir exámenes.");
          router.push(`/app/session/${sessionId}`);
        },
      },
    );
  };

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-12">
      {phase === "form" && (
        <>
          <RecentSessionCard />
          <div className="flex flex-col gap-1">
            <h1 className="text-4xl font-bold text-foreground">
              Crear una nueva sesión de corrección
            </h1>
            {!atLimit && !sessionsLoading && (
              <p className="text-lg mt-8">
                Desde aquí puedes crear una <b>sesión de corrección</b> para que <i>Korrijo</i> evalúe instancias de un examen. Pero antes necesitamos que nos proporciones
                algunos <b>datos</b> y <b>ficheros</b>:
              </p>
            )}
          </div>

          {sessionsLoading ? (
            <div className="flex flex-1 items-center justify-center py-24">
              <Loader2 className="size-10 animate-spin text-primary" />
            </div>
          ) : atLimit ? (
            <div className="flex flex-col items-center gap-8 px-6 py-16 text-center">
              <TriangleAlert className="size-20 text-amber-500" />
              <div className="flex flex-col gap-4">
                <p className="text-3xl font-semibold text-foreground">
                  Has alcanzado el límite de {MAX_ACTIVE_SESSIONS} sesiones de
                  corrección
                </p>
                <p className="text-xl text-foreground">
                  Si quieres crear una nueva, primero tendrás que borrar alguna
                  de las que ya tienes.
                </p>
              </div>
              <Button asChild size="lg" className="text-lg">
                <Link href="/app/history">Ir a mis sesiones</Link>
              </Button>
            </div>
          ) : (
            <NewSessionForm onSubmit={handleFormSubmit} />
          )}
        </>
      )}

      {phase === "uploading" && (
        <div className="flex flex-1 flex-col items-center justify-center gap-6 py-16 text-center">
          {uploadError ? (
            <>
              <TriangleAlert className="size-16 text-destructive" />
              <div className="flex flex-col gap-2">
                <p className="text-2xl text-foreground">
                  Algo ha fallado al procesar la rúbrica proporcionada...
                </p>
              </div>
              <div className="flex gap-4">
                <Button
                  variant="outline"
                  size="lg"
                  className="text-lg"
                  onClick={handleStartOver}
                >
                  Empezar de nuevo
                </Button>
                <Button size="lg" className="text-lg" onClick={handleRetry}>
                  Reintentar
                </Button>
              </div>
            </>
          ) : (
            <>
              <Loader2 className="size-10 animate-spin text-primary" />
              <p
                className={`font-medium ${
                  doneCount < jobs.length &&
                  jobs[doneCount].kind === "rubric"
                    ? "text-xl"
                    : "text-lg"
                }`}
              >
                {doneCount < jobs.length
                  ? jobLabel(jobs[doneCount].kind)
                  : "Preparando tu sesión..."}
              </p>
            </>
          )}
        </div>
      )}

      {phase === "review" && values && (
        <RubricReview
          maxScore={values.maxScore}
          initialItems={rubricItems}
          initialWarning={rubricWarning}
          onConfirm={handleConfirmRubric}
          confirming={validate.isPending}
          error={validate.isError ? messageFrom(validate.error) : null}
        />
      )}
    </section>
  );
}
