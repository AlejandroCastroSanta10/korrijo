"use client";

import { useState } from "react";
import { Download, Loader2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ApiError, fetchBlob } from "@/lib/api";
import { downloadBlob } from "@/lib/utils";
import { useExamDetail, type GradingResultRead } from "@/lib/hooks/sessions";

type ResultView = "feedback" | "rubric";

interface ExamResultDialogProps {
  sessionId: string;
  examId: string | null;
  view: ResultView;
  maxScore: number;
  onClose: () => void;
}

const stem = (filename: string) => filename.replace(/\.[^.]+$/, "");

function RubricTable({
  result,
  maxScore,
}: {
  result: GradingResultRead;
  maxScore: number;
}) {
  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-3">
        {result.rubric_filled.map((item, i) => (
          <li
            key={i}
            className="flex flex-col gap-1 rounded-xl border border-input bg-input/20 p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="font-medium text-foreground">
                {item.item_name}
              </span>
              <span className="shrink-0 font-semibold text-foreground">
                {item.assigned_score.toLocaleString("es", {
                  maximumFractionDigits: 2,
                })}{" "}
                / {item.max_score.toLocaleString("es")}
              </span>
            </div>
            {item.comment && (
              <p className="text-sm text-muted-foreground">{item.comment}</p>
            )}
          </li>
        ))}
      </ul>
      <div className="flex items-center justify-between rounded-xl bg-muted px-4 py-3">
        <span className="font-semibold text-foreground">Nota propuesta</span>
        <span className="text-lg font-bold text-foreground">
          {result.total_score.toLocaleString("es", {
            maximumFractionDigits: 2,
          })}{" "}
          / {maxScore.toLocaleString("es")}
        </span>
      </div>
    </div>
  );
}

export default function ExamResultDialog({
  sessionId,
  examId,
  view,
  maxScore,
  onClose,
}: ExamResultDialogProps) {
  const { data: exam, isLoading, isError } = useExamDetail(sessionId, examId);
  const [downloading, setDownloading] = useState(false);

  const isFeedback = view === "feedback";
  const title = isFeedback ? "Informe de la corrección" : "Rúbrica rellenada";

  const handleDownload = async () => {
    if (!examId || !exam) return;
    setDownloading(true);
    try {
      const file = isFeedback ? "feedback.pdf" : "rubric.pdf";
      const blob = await fetchBlob(
        `/api/sessions/${sessionId}/exams/${examId}/${file}`,
      );
      const prefix = isFeedback ? "informe" : "rubrica";
      downloadBlob(blob, `${prefix}_${stem(exam.filename)}.pdf`);
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "No se pudo descargar el PDF.",
      );
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Dialog open={!!examId} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {exam && <DialogDescription>{exam.filename}</DialogDescription>}
        </DialogHeader>

        <div className="-mx-1 flex-1 overflow-y-auto px-1">
          {isLoading && (
            <div className="flex justify-center py-12">
              <Loader2 className="size-8 animate-spin text-primary" />
            </div>
          )}

          {isError && (
            <p className="flex items-center gap-2 py-8 text-sm text-destructive">
              <TriangleAlert className="size-4" />
              No se pudo cargar el resultado.
            </p>
          )}

          {exam && !exam.result && !isLoading && (
            <p className="py-8 text-sm text-muted-foreground">
              Este examen aún no tiene resultado disponible.
            </p>
          )}

          {exam?.result &&
            (isFeedback ? (
              <p className="text-sm whitespace-pre-wrap text-foreground">
                {exam.result.feedback_report}
              </p>
            ) : (
              <RubricTable result={exam.result} maxScore={maxScore} />
            ))}
        </div>

        {exam?.result && (
          <div className="flex justify-end border-t border-border pt-4">
            <Button onClick={handleDownload} disabled={downloading}>
              {downloading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Download className="size-4" />
              )}
              Descargar PDF
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
