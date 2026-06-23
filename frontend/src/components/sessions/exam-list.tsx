"use client";

import { FileText, Loader2, FileSearch, ClipboardCheck} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ExamRead, ExamStatus } from "@/lib/hooks/sessions";

type ResultView = "feedback" | "rubric";

interface ExamListProps {
  exams: ExamRead[];
  maxScore: number;
  onOpenResult: (examId: string, view: ResultView) => void;
}

const DOT: Record<ExamStatus, string> = {
  pending: "bg-blue-500",
  processing: "bg-amber-400",
  completed: "bg-green-500",
  error: "bg-destructive",
};

function StatusDot({ status }: { status: ExamStatus }) {
  return (
    <span
      className={`size-2.5 shrink-0 rounded-full ${DOT[status]} ${
        status === "processing" ? "animate-pulse" : ""
      }`}
    />
  );
}

function formatScore(score: number, maxScore: number): string {
  return `${score.toLocaleString("es", {
    maximumFractionDigits: 2,
  })} / ${maxScore.toLocaleString("es")}`;
}

function ExamRow({
  exam,
  maxScore,
  onOpenResult,
}: {
  exam: ExamRead;
  maxScore: number;
  onOpenResult: ExamListProps["onOpenResult"];
}) {
  const passed = exam.total_score != null && exam.total_score >= maxScore / 2;

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-2xl border border-input bg-card px-6 py-5">
      <StatusDot status={exam.status} />
      <FileText className="size-5 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1 truncate text-base font-medium text-foreground">
        {exam.filename}
      </span>

      {exam.status === "pending" && (
        <span className="text-base text-muted-foreground">En cola</span>
      )}

      {exam.status === "processing" && (
        <span className="flex items-center gap-1.5 text-base">
          <Loader2 className="size-4 animate-spin" />
          Procesando...
        </span>
      )}

      {exam.status === "error" && (
        <span className="text-base text-destructive">
          {exam.error_message ?? "Error al corregir el examen."}
        </span>
      )}

      {exam.status === "completed" && (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <span
            className={`text-xl font-bold ${
              passed
                ? "text-green-600 dark:text-green-500"
                : "text-destructive"
            }`}
          >
            {exam.total_score != null
              ? formatScore(exam.total_score, maxScore)
              : "—"}
          </span>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="outline"
              size="lg"
              className="text-base"
              onClick={() => onOpenResult(exam.id, "feedback")}
            >
              <FileSearch className="size-4" />
              Ver informe de <i>feedback</i>
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="text-base"
              onClick={() => onOpenResult(exam.id, "rubric")}
            >
              <ClipboardCheck className="size-4" />
              Ver rúbrica rellenada
            </Button>
          </div>
        </div>
      )}
    </li>
  );
}

export default function ExamList({
  exams,
  maxScore,
  onOpenResult,
}: ExamListProps) {
  if (exams.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 px-6 py-16 text-center">
        <p className="text-lg font-medium text-foreground">
          Aún no se han procesado exámenes en esta sesión
        </p>
        <p className="max-w-md text-base text-muted-foreground">
          Sube exámenes arriba y aquí verás su estado y resultados
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-xl font-semibold text-foreground mb-4">
        Subidos ({exams.length})
      </h2>
      <ul className="flex flex-col gap-3">
        {exams.map((exam) => (
          <ExamRow
            key={exam.id}
            exam={exam}
            maxScore={maxScore}
            onOpenResult={onOpenResult}
          />
        ))}
      </ul>
    </div>
  );
}
