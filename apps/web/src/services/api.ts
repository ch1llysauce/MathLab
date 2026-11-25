import type {
  AIExplainRequest,
  AIExplainResponse,
  ApiErrorEnvelope,
  CellInput,
  ComputeRequest,
  ComputeResponse,
  HealthResponse,
  NotebookCell,
  NotebookExecuteResponse,
  NotebookHistoryEntry,
  NotebookMode,
  NotebookResponse,
  NotebookSummary,
  OperationInfo,
  PlotRequest,
  PlotResponse,
  VariableBinding,
  WorkedExample,
} from "../types/compute";
import { supabase } from "./supabase";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  (import.meta.env.PROD ? "" : "http://localhost:8000");

export class ApiClientError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: Record<string, unknown>;

  constructor(
    message: string,
    code = "API_ERROR",
    status = 500,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  if (!supabase) return {};
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const errBody = data as ApiErrorEnvelope | null;
    throw new ApiClientError(
      errBody?.error?.message ?? `Request failed with status ${response.status}`,
      errBody?.error?.code ?? "HTTP_ERROR",
      response.status,
      errBody?.error?.details
    );
  }
  return data as T;
}

export function fetchHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/v1/health");
}

export function fetchOperations(): Promise<OperationInfo[]> {
  return requestJson<OperationInfo[]>("/api/v1/compute/operations");
}

export function runCompute(payload: ComputeRequest): Promise<ComputeResponse> {
  return requestJson<ComputeResponse>("/api/v1/compute", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchPlot(payload: PlotRequest): Promise<PlotResponse> {
  return requestJson<PlotResponse>("/api/v1/visualization/plot", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listNotebooks(): Promise<NotebookSummary[]> {
  return requestJson<NotebookSummary[]>("/api/v1/notebooks");
}

export function createNotebook(payload: {
  title: string;
  mode: NotebookMode;
  cells: CellInput[];
}): Promise<NotebookResponse> {
  return requestJson<NotebookResponse>("/api/v1/notebooks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getNotebook(notebookId: string): Promise<NotebookResponse> {
  return requestJson<NotebookResponse>(`/api/v1/notebooks/${notebookId}`);
}

export function updateNotebook(
  notebookId: string,
  payload: { title?: string; mode?: NotebookMode; cells?: CellInput[] }
): Promise<NotebookResponse> {
  return requestJson<NotebookResponse>(`/api/v1/notebooks/${notebookId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function executeNotebook(
  notebookId: string,
  payload: { only_stale?: boolean; up_to_cell_id?: string | null } = {}
): Promise<NotebookExecuteResponse> {
  return requestJson<NotebookExecuteResponse>(`/api/v1/notebooks/${notebookId}/execute`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function executeStatelessNotebook(payload: {
  id?: string;
  title: string;
  mode: NotebookMode;
  created_at?: string;
  cells: NotebookCell[];
  variables: Record<string, VariableBinding>;
  only_stale?: boolean;
  up_to_cell_id?: string | null;
}): Promise<NotebookExecuteResponse> {
  return requestJson<NotebookExecuteResponse>("/api/v1/notebooks/execute-stateless", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteNotebook(notebookId: string): Promise<void> {
  return requestJson<void>(`/api/v1/notebooks/${notebookId}`, {
    method: "DELETE",
  });
}

export function exportNotebook(
  notebookId: string,
  format: "markdown" | "json" = "markdown"
): Promise<{ filename: string; media_type: string; content: string }> {
  return requestJson<{ filename: string; media_type: string; content: string }>(
    `/api/v1/notebooks/${notebookId}/export?format=${format}`
  );
}

export function listNotebookHistory(notebookId: string): Promise<NotebookHistoryEntry[]> {
  return requestJson<NotebookHistoryEntry[]>(`/api/v1/notebooks/${notebookId}/history`);
}

export function explainMath(payload: AIExplainRequest): Promise<AIExplainResponse> {
  return requestJson<AIExplainResponse>("/api/v1/ai/explain", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listWorkedExamples(): Promise<WorkedExample[]> {
  return requestJson<WorkedExample[]>("/api/v1/ai/examples");
}

export { API_BASE_URL };
