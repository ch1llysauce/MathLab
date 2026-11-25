import type { PlotSeed } from "../types/compute";

const OPERATION_LABELS: Record<string, string> = {
  assign: "Assign Variable  (f = ...)",
  simplify: "Simplify",
  expand: "Expand",
  factor: "Factor",
  solve: "Solve Equation  (= 0)",
  differentiate: "Differentiate  (d/dx)",
  integrate: "Integrate  (∫)",
  limit: "Limit  (lim)",
  partial_derivative: "Partial Derivative  (∂/∂x)",
  taylor_series: "Taylor Series  (∑)",
  solve_ode: "Solve ODE  (y' = f)",
  linear_system_solve: "Linear System  (Ax = b)",
  numerical_eval: "Numerical Evaluate  (≈)",
  root_find: "Root Find  (f(x) = 0)",
  numerical_integrate: "Numerical Integrate  (∫ num)",
  matrix_add: "Matrix Add  (A + B)",
  matrix_multiply: "Matrix Multiply  (A × B)",
  matrix_transpose: "Matrix Transpose  (Aᵀ)",
  matrix_determinant: "Matrix Determinant  (|A|)",
  matrix_inverse: "Matrix Inverse  (A⁻¹)",
  matrix_rank: "Matrix Rank",
  matrix_rref: "Matrix RREF",
  matrix_eigenvalues: "Matrix Eigenvalues  (λ)",
  matrix_eigenvectors: "Matrix Eigenvectors  (Av = λv)",
};

export const OPS_WITH_VARIABLE = new Set([
  "differentiate",
  "integrate",
  "limit",
  "solve",
  "partial_derivative",
  "taylor_series",
  "solve_ode",
  "root_find",
  "numerical_integrate",
]);

export const OP_VAR_LABELS: Record<string, string> = {
  solve: "Solve for",
  differentiate: "Respect to",
  integrate: "Respect to",
  partial_derivative: "Respect to",
};

export function isMatrixLikeOperation(op: string): boolean {
  const clean = op.trim().toLowerCase();
  return clean.startsWith("matrix_") || clean === "linear_system_solve";
}

const UPPERCASE_WORDS = new Set(["ode", "rref", "ivp", "2d", "3d"]);

export function formatHumanLabel(raw: string): string {
  return raw
    .split("_")
    .filter(Boolean)
    .map((word) => {
      const lower = word.toLowerCase();
      if (UPPERCASE_WORDS.has(lower)) return word.toUpperCase();
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(" ");
}

export function formatOperationLabel(op: string): string {
  const clean = op.trim().toLowerCase();
  if (OPERATION_LABELS[clean]) {
    return OPERATION_LABELS[clean];
  }
  return formatHumanLabel(clean);
}

/** Strips leading `var =` inline assignment for expression ops; converts `lhs = rhs` equations for Solve/Root Find into `lhs - rhs` expressions for 2D plotting. */
export function preparePlottableExpression(
  raw: string,
  operation: string | null | undefined
): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  const op = (operation ?? "simplify").trim().toLowerCase();
  if (op === "solve" || op === "root_find") {
    const parts = trimmed.split("=");
    if (parts.length === 2) {
      const lhs = parts[0].trim();
      const rhs = parts[1].trim();
      if (lhs && rhs) {
        return /^0(?:\.0+)?$/.test(rhs) ? lhs : `(${lhs}) - (${rhs})`;
      }
    }
    return trimmed;
  }
  if (op === "solve_ode") {
    return trimmed;
  }
  return trimmed.replace(/^[a-zA-Z][a-zA-Z0-9_]{0,15}\s*=\s*/, "").trim();
}

/** Extracts a single-function comparison expression from a compute result, skipping multi-root/equation strings. */
export function extractPlottableCompareResult(
  rawResult: string | null | undefined,
  resolvedInput: string
): string | undefined {
  const raw = rawResult?.trim();
  if (!raw) return undefined;
  const cleaned = raw
    .replace(/\s*\+\s*C$/i, "")
    .replace(/^[a-zA-Z][a-zA-Z0-9_]*\([a-zA-Z][a-zA-Z0-9_]*\)\s*=\s*/, "")
    .trim();
  if (
    !cleaned ||
    cleaned === resolvedInput ||
    cleaned.toLowerCase() === "no solution" ||
    cleaned.includes("[") ||
    cleaned.includes(",") ||
    cleaned.includes("=")
  ) {
    return undefined;
  }
  return cleaned;
}

/** Builds a Visualization Studio matrix plot seed from cell/compute options and optional matrix result metadata. */
export function buildMatrixPlotSeed(
  operation: string,
  options: Record<string, unknown> | null | undefined,
  resultDetails?: Record<string, unknown> | null
): Omit<PlotSeed, "seq"> | null {
  const opts = options || {};
  const rawA = opts.matrix ?? opts.matrix_a;
  if (!Array.isArray(rawA) || rawA.length === 0 || !Array.isArray(rawA[0])) {
    return null;
  }

  const clean = operation.trim().toLowerCase();
  const resultMat =
    resultDetails &&
    Array.isArray(resultDetails.matrix) &&
    resultDetails.matrix.length > 0 &&
    Array.isArray(resultDetails.matrix[0])
      ? (resultDetails.matrix as (number | string)[][])
      : undefined;

  const optMatB =
    Array.isArray(opts.matrix_b) && opts.matrix_b.length > 0 && Array.isArray(opts.matrix_b[0])
      ? (opts.matrix_b as (number | string)[][])
      : undefined;

  const vector =
    clean === "linear_system_solve" && Array.isArray(opts.vector)
      ? (opts.vector as (number | string)[])
      : undefined;

  return {
    plotType: "matrix",
    matrix: rawA as (number | string)[][],
    matrixB: resultMat ?? optMatB,
    vector,
    matrixView: clean === "linear_system_solve" ? "system" : "auto",
  };
}
