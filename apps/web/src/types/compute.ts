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

export interface ReasoningAnalysis {
  classification: {
    domain: string;
    problem_type: string;
    variables: string[];
    features: Record<string, unknown>;
  };
  assumptions: {
    declared: Record<string, string>;
    constraints: Array<{
      expression: string;
      condition: string;
      reason: string;
      source: string;
    }>;
    notes: string[];
  };
  rules: Array<{
    rule_id: string;
    description: string;
    passed: boolean;
    severity: string;
    message: string;
  }>;
  selection: {
    recommended_operation: string;
    recommended_method: string;
    applicable: boolean;
    rationale: string;
    candidates: Array<{
      operation: string;
      method: string;
      applicable: boolean;
      reason: string;
    }>;
  };
}

export interface VerificationCheckItem {
  check_type: string;
  name: string;
  passed: boolean | null;
  message: string;
  residual: number | null;
  details: Record<string, unknown>;
}

export interface VerificationResult {
  status: "verified" | "numerical_support" | "partial" | "inconclusive";
  verified: boolean;
  discrepancy_detected: boolean;
  summary: string;
  checks: VerificationCheckItem[];
}

export interface ComputeResponse {
  operation: string;
  input: string | null;
  result: string;
  latex: string;
  metadata: ComputeMetadata;
  reasoning?: ReasoningAnalysis | null;
  verification?: VerificationResult | null;
}

export type NotebookMode = "computational" | "learning";
export type CellStatus = "idle" | "valid" | "stale" | "error";

export interface CellInput {
  id?: string;
  cell_type: "math" | "markdown" | "ai";
  operation?: string | null;
  expression?: string | null;
  variable?: string | null;
  assign_to?: string | null;
  assumptions?: Record<string, string>;
  options?: Record<string, unknown>;
}

export interface CellResult {
  result_text: string;
  result_latex: string;
  metadata: Record<string, unknown>;
  reasoning?: ReasoningAnalysis | null;
  verification?: VerificationResult | null;
  executed_at: string;
}

export interface NotebookCell {
  id: string;
  notebook_id: string;
  position: number;
  cell_type: "math" | "markdown" | "ai";
  operation: string | null;
  expression: string | null;
  variable: string | null;
  assign_to: string | null;
  assumptions: Record<string, string>;
  options: Record<string, unknown>;
  status: CellStatus;
  depends_on: string[];
  error_message: string | null;
  result: CellResult | null;
}

export interface VariableBinding {
  symbol_name: string;
  value_expr: string;
  value_latex: string;
  cell_id: string;
  assumptions: Record<string, string>;
}

export interface NotebookSummary {
  id: string;
  title: string;
  mode: NotebookMode;
  cell_count: number;
  created_at: string;
  updated_at: string;
}

export interface NotebookResponse {
  id: string;
  title: string;
  mode: NotebookMode;
  created_at: string;
  updated_at: string;
  cells: NotebookCell[];
  variables: Record<string, VariableBinding>;
}

export interface NotebookExecuteResponse {
  notebook: NotebookResponse;
  executed_cell_ids: string[];
  skipped_cell_ids: string[];
  history_id: string;
}

export interface NotebookHistoryEntry {
  id: string;
  notebook_id: string;
  created_at: string;
  executed_cell_ids: string[];
  skipped_cell_ids: string[];
  notebook?: NotebookResponse | null;
}

export interface AIExplainRequest {
  prompt?: string | null;
  operation?: string | null;
  expression?: string | null;
  variable?: string | null;
  assumptions?: Record<string, string> | null;
  options?: Record<string, unknown>;
  mode: NotebookMode;
}

export interface AIExplainResponse {
  mode: NotebookMode;
  interpretation_source: string;
  explanation_source: string;
  operation: string;
  expression: string | null;
  variable?: string | null;
  options?: Record<string, unknown>;
  result: string;
  latex: string;
  summary: string;
  steps: Array<{ title: string; content: string }>;
  reasoning: ReasoningAnalysis;
  verification: VerificationResult;
}

export interface WorkedExample {
  id: string;
  title: string;
  domain: string;
  difficulty: string;
  description: string;
  prompt: string | null;
  operation: string;
  expression: string | null;
  variable: string | null;
  options: Record<string, unknown>;
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

export interface PlotRequest {
  expression?: string | null;
  expressions?: string[];
  plot_type: "2d" | "3d" | "matrix";
  variables: string[];
  x_range?: [number, number];
  y_range?: [number, number];
  num_points?: number;
  grid_size?: number;
  parameters?: Record<string, number>;
  include_derivative?: boolean;
  include_integral?: boolean;
  tangent_at?: number | null;
  tangent_y?: number | null;
  detect_features?: boolean;
  matrix?: (number | string)[][];
  matrix_b?: (number | string)[][];
  vector?: (number | string)[];
  matrix_view?: "auto" | "transform" | "system" | "heatmap" | "surface";
}

export interface PlotSeed {
  expr?: string;
  compareExpr?: string;
  variable?: string;
  plotType?: "2d" | "3d" | "matrix";
  matrix?: (number | string)[][];
  matrixB?: (number | string)[][];
  vector?: (number | string)[];
  matrixView?: "auto" | "transform" | "system" | "heatmap" | "surface";
  seq: number;
}

export interface PlotKeyPoint {
  kind: string;
  x: number;
  y: number;
  label: string;
  derivative_expr?: string | null;
}

export interface PlotResponse {
  plot_type: "2d" | "3d";
  traces: Record<string, unknown>[];
  key_points: PlotKeyPoint[];
  layout: {
    title: string;
    xaxis_title: string;
    yaxis_title: string;
    zaxis_title?: string | null;
  };
  metadata: Record<string, unknown>;
}
