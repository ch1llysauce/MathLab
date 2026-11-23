export interface ComputeRequest {
  operation: string;
  expression?: string | null;
  variable?: string | null;
  assumptions?: Record<string, string> | null;
  options?: Record<string, unknown>;
}

export interface ComputeMetadata {
  domain: string;
  method: string;
  details: Record<string, unknown>;
}

export interface ComputeResponse {
  operation: string;
  input: string | null;
  result: string;
  latex: string;
  metadata: ComputeMetadata;
}

export interface OperationInfo {
  name: string;
  domain: string;
  description: string;
  aliases: string[];
}

export interface HealthResponse {
  status: string;
  environment: string;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
