"use client";

import { useRef, useState } from "react";
import { FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { cn, formatBytes } from "@/lib/utils";
import { ApiError } from "@/lib/api";
import {
  useUploadExams,
  EXAM_ALLOWED_EXTENSIONS,
  MAX_EXAM_BYTES,
  MAX_EXAMS_PER_UPLOAD,
  MAX_EXAMS_IN_QUEUE,
} from "@/lib/hooks/sessions";

const ACCEPT = EXAM_ALLOWED_EXTENSIONS.join(",");

interface ExamUploadProps {
  sessionId: string;
  // Exámenes de la sesión que siguen en curso (pending o processing).
  activeExamCount: number;
}

// Validación cliente coherente con el backend.
function validateBatch(files: File[], activeExamCount: number): string | null {
  if (files.length > MAX_EXAMS_PER_UPLOAD) {
    return `Máximo ${MAX_EXAMS_PER_UPLOAD} exámenes por subida`;
  }
  if (activeExamCount + files.length > MAX_EXAMS_IN_QUEUE) {
    const free = Math.max(0, MAX_EXAMS_IN_QUEUE - activeExamCount);
    return free === 0
      ? `La cola de corrección está llena (máximo ${MAX_EXAMS_IN_QUEUE-1} esperando a ser procesados). Espera a que se corrija alguno antes de subir más`
      : `Solo puede haber ${MAX_EXAMS_IN_QUEUE} exámenes a la vez en la cola de corrección. Ahora mismo puedes subir ${free} más`;
  }
  for (const file of files) {
    const extOk = EXAM_ALLOWED_EXTENSIONS.some((ext) =>
      file.name.toLowerCase().endsWith(ext),
    );
    if (!extOk) {
      return `«${file.name}» no tiene un formato válido. Admitidos: ${EXAM_ALLOWED_EXTENSIONS.join(", ")}`;
    }
    if (file.size > MAX_EXAM_BYTES) {
      return `«${file.name}» supera los ${formatBytes(MAX_EXAM_BYTES)}.`;
    }
  }
  return null;
}

export default function ExamUpload({
  sessionId,
  activeExamCount,
}: ExamUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const upload = useUploadExams(sessionId);

  const busy = upload.isPending;

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    const errorMsg = validateBatch(files, activeExamCount);
    if (errorMsg) {
      toast.error(errorMsg);
      return;
    }
    upload.mutate(files, {
      onSuccess: (created) =>
        toast.success(
          created.length === 1
            ? "Examen en cola de corrección."
            : `${created.length} exámenes en cola de corrección.`,
        ),
      onError: (err) =>
        toast.error(
          err instanceof ApiError
            ? err.message
            : "No se pudieron subir los exámenes. Inténtalo de nuevo.",
        ),
    });
  };

  return (
    <>
      <button
        type="button"
        onClick={() => !busy && inputRef.current?.click()}
        disabled={busy}
        onDragOver={(e) => {
          e.preventDefault();
          if (!busy) setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (!busy) handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex min-h-44 w-full flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-input bg-input/20 px-6 py-12 text-center transition-colors",
          "hover:bg-input/40 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 outline-none mt-4",
          dragActive && "border-ring bg-input/40",
          busy && "pointer-events-none opacity-60",
        )}
      >
        {upload.isPending ? (
          <>
            <Loader2 className="size-10 animate-spin text-primary" />
            <span className="text-lg font-medium text-foreground">
              Subiendo exámenes...
            </span>
          </>
        ) : (
          <>
            <FileText className="size-10 text-muted-foreground" strokeWidth={1.5} />
            <span className="text-lg font-lg text-foreground">
              Arrastra aquí los exámenes a corregir
            </span>
            <span className="text-medium text-muted-foreground">
              O haz click aquí para seleccionar
            </span>
          </>
        )}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        multiple
        className="hidden"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </>
  );
}
