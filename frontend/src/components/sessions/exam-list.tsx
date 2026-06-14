"use client";

import { FileText, Loader2, FileSearch, ClipboardCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ExamRead, ExamStatus } from "@/lib/hooks/sessions";

type ResultView = "feedback" | "rubric";

interface ExamListProps {
  exams: ExamRead[];
  maxScore: number;
  onOpenResult: (examId: string, view: ResultView) => void;
}

const DOT: Record<ExamStatus, string> = {
  pending: "bg-amber-400",
  processing: "bg-blue-500",
  completed: "bg-emerald-500",
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
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-input py-4 last:border-b-0">
      <StatusDot status={exam.status} />
      <FileText className="size-4 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1 truncate font-medium text-foreground">
        {exam.filename}
      </span>

      {exam.status === "pending" && (
        <span className="text-sm text-muted-foreground">En cola</span>
      )}

      {exam.status === "processing" && (
        <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Procesando...
        </span>
      )}

      {exam.status === "error" && (
        <span className="text-sm text-destructive">
          {exam.error_message ?? "Error al corregir el examen."}
        </span>
      )}

      {exam.status === "completed" && (
        <div className="flex items-center gap-3">
          <span
            className={`text-lg font-bold ${
              passed
                ? "text-emerald-600 dark:text-emerald-500"
                : "text-destructive"
            }`}
          >
            {exam.total_score != null
              ? formatScore(exam.total_score, maxScore)
              : "—"}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenResult(exam.id, "feedback")}
          >
            <FileSearch className="size-4" />
            Ver informe
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenResult(exam.id, "rubric")}
          >
            <ClipboardCheck className="size-4" />
            Ver rúbrica
          </Button>
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
      <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-input bg-input/10 px-6 py-12 text-center">
        <FileText className="size-8 text-muted-foreground" strokeWidth={1.5} />
        <p className="font-medium text-foreground">Aún no hay exámenes</p>
        <p className="text-sm text-muted-foreground">
          Sube exámenes arriba y aquí verás su estado y los resultados de la
          corrección.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-xl font-semibold text-foreground">
        Exámenes ({exams.length})
      </h2>
      <ul className="flex flex-col">
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
