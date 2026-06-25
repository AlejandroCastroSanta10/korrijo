import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

export interface RubricItemResult {
  item_name: string;
  assigned_score: number;
  max_score: number;
  comment: string;
}

export interface GradingResultRead {
  total_score: number;
  rubric_filled: RubricItemResult[];
  feedback_report: string;
  created_at: string;
}

export interface ExamDetail extends ExamRead {
  // result solo viene relleno cuando el examen está "completed".
  result: GradingResultRead | null;
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
  last_exam_at: string | null;
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

// Máximo de sesiones activas por usuario. Coherente con el backend
export const MAX_ACTIVE_SESSIONS = 4;

export function useSessions() {
  return useQuery({
    queryKey: ["sessions", "list"],
    queryFn: () => api.get<SessionRead[]>("/api/sessions"),
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del<void>(`/api/sessions/${id}`),
    // Refresca el listado, la sesión reciente y cualquier vista de sesión.
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}

// --- Fase 2: corrección de exámenes ---

// Coherente con el backend.
export const EXAM_ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"];
export const MAX_EXAM_BYTES = 5 * 1024 * 1024; // 5 MB por examen
export const MAX_EXAMS_PER_UPLOAD = 3;
// Máximo de exámenes a la vez en cola de corrección (uno procesándose y hasta
// dos esperando). Equivale a "no más de 2 esperando a ser procesados".
export const MAX_EXAMS_IN_QUEUE = 3;
// Intervalo de polling mientras haya exámenes sin terminar.
export const POLL_INTERVAL_MS = 5000;

export const isExamActive = (status: ExamStatus) =>
  status === "pending" || status === "processing";

export function useSession(id: string) {
  return useQuery({
    queryKey: ["sessions", id],
    queryFn: () => api.get<SessionDetail>(`/api/sessions/${id}`),
    // Polling: refresca mientras algún examen siga en curso; se detiene solo.
    refetchInterval: (query) =>
      query.state.data?.exams.some((e) => isExamActive(e.status))
        ? POLL_INTERVAL_MS
        : false,
  });
}

export function useExamDetail(sessionId: string, examId: string | null) {
  return useQuery({
    queryKey: ["sessions", sessionId, "exams", examId],
    queryFn: () =>
      api.get<ExamDetail>(`/api/sessions/${sessionId}/exams/${examId}`),
    enabled: !!examId,
  });
}

export function useUploadExams(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData();
      files.forEach((file) => form.append("files", file));
      return api.postForm<ExamRead[]>(
        `/api/sessions/${sessionId}/exams`,
        form,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions", sessionId] });
    },
  });
}
