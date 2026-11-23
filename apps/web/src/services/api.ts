import type {
  ApiErrorEnvelope,
  ComputeRequest,
  ComputeResponse,
  HealthResponse,
  OperationInfo,
} from "../types/compute";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

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

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

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

export { API_BASE_URL };
