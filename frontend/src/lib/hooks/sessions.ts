import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// --- Tipos espejo de los schemas del backend (app/schemas/session.py) ---

export type SessionStatus = "draft" | "ready" | "archived";
export type ExamStatus = "pending" | "processing" | "completed" | "error";
export type DocumentKind = "context" | "model_exam" | "rubric";

export interface RubricItem {
  name: string;
  max_score: number;
  description: string;
}

export interface RubricStructured {
  items: RubricItem[];
  total_max_score: number;
  warning: string | null;
}

export interface SessionDocument {
  id: string;
  kind: DocumentKind;
  filename: string;
  size_bytes: number;
  mime_type: string;
  created_at: string;
}

export interface DocumentUploadResponse extends SessionDocument {
  extracted_text: string | null;
  // Solo viene relleno al subir una rúbrica.
  rubric: RubricStructured | null;
}

export interface ExamRead {
  id: string;
  filename: string;
  status: ExamStatus;
  total_score: number | null;
  error_message: string | null;
  created_at: string;
}

export interface SessionRead {
  id: string;
  name: string;
  max_score: number;
  status: SessionStatus;
  context_instructions: string | null;
  model_exam_instructions: string | null;
  created_at: string;
  updated_at: string;
  graded_count: number;
  passed_count: number;
  failed_count: number;
  average_score: number | null;
}

export interface SessionDetail extends SessionRead {
  documents: SessionDocument[];
  exams: ExamRead[];
}

// --- Hooks ---

export interface CreateSessionBody {
  name: string;
  max_score: number;
  context_instructions?: string | null;
  model_exam_instructions?: string | null;
}

export function useCreateSession() {
  return useMutation({
    mutationFn: (body: CreateSessionBody) =>
      api.post<SessionDetail>("/api/sessions", body),
  });
}

export interface UploadDocumentVars {
  sessionId: string;
  kind: DocumentKind;
  file: File;
}

export function useUploadDocument() {
  return useMutation({
    mutationFn: ({ sessionId, kind, file }: UploadDocumentVars) => {
      const form = new FormData();
      form.append("kind", kind);
      form.append("file", file);
      return api.postForm<DocumentUploadResponse>(
        `/api/sessions/${sessionId}/documents`,
        form,
      );
    },
  });
}

export interface ValidateRubricVars {
  sessionId: string;
  items: RubricItem[];
}

export function useValidateRubric() {
  return useMutation({
    mutationFn: ({ sessionId, items }: ValidateRubricVars) =>
      api.post<SessionDetail>(`/api/sessions/${sessionId}/rubric/validate`, {
        items,
      }),
  });
}

export function useRecentSession() {
  return useQuery({
    queryKey: ["sessions", "recent"],
    queryFn: () => api.get<SessionRead | null>("/api/sessions/recent"),
  });
}
