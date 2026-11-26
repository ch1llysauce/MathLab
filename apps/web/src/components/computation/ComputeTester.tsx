import { FormEvent, useRef, useState } from "react";

import { ApiClientError, explainMath, runCompute } from "../../services/api";
import type {
  AIExplainResponse,
  ComputeResponse,
  NotebookMode,
  NotebookSummary,
  OperationInfo,
  PlotSeed,
} from "../../types/compute";
import {
  backspaceInputElement,
  formatCellNotationLatex,
  insertIntoInputElement,
} from "../../utils/mathPreview";
import {
  buildMatrixPlotSeed,
  extractPlottableCompareResult,
  formatHumanLabel,
  formatOperationLabel,
  isMatrixLikeOperation,
  OP_VAR_LABELS,
  OPS_WITH_VARIABLE,
  preparePlottableExpression,
} from "../../utils/operationLabels";
import { AssumptionsEditor } from "../common/AssumptionsEditor";
import { ErrorAlert } from "../common/ErrorAlert";
import { MathKeypad } from "../common/MathKeypad";
import {
  MatrixGridEditor,
  type MatrixData,
  normalizeMatrixData,
  normalizeVectorData,
  VectorGridEditor,
} from "../common/MatrixGridEditor";
import { Modal } from "../common/Modal";
import { StepByStepGuide } from "../common/StepByStepGuide";
import { showToast } from "../common/Toast";
import type { IncomingNotebookCellSeed } from "../notebook/NotebookWorkbench";
import { ExplainableOutputPanel } from "./ExplainableOutputPanel";
import { LatexBlock } from "./LatexBlock";

interface Preset {
  label: string;
  operation: string;
  expression: string;
  variable: string;
  options: Record<string, unknown>;
}

const PRESETS: Preset[] = [
  {
    label: "Differentiate",
    operation: "differentiate",
    expression: "x^3 + 2*x",
    variable: "x",
    options: {},
  },
  {
    label: "Integrate",
    operation: "integrate",
    expression: "2*x",
    variable: "x",
    options: {},
  },
  {
    label: "Solve Equation",
    operation: "solve",
    expression: "x^2 - 5*x + 6 = 0",
    variable: "x",
    options: {},
  },
  {
    label: "Limit",
    operation: "limit",
    expression: "sin(x)/x",
    variable: "x",
    options: { point: "0" },
  },
  {
    label: "Matrix Eigenvalues",
    operation: "matrix_eigenvalues",
    expression: "",
    variable: "",
    options: { matrix: [[2, 0], [0, 3]] },
  },
  {
    label: "Root Find",
    operation: "root_find",
    expression: "x^2 - 2",
    variable: "x",
    options: { bracket: [1, 2] },
  },
];

interface ComputeTesterProps {
  operations: OperationInfo[];
  onPlotExpression?: (seed: Omit<PlotSeed, "seq">) => void;
  onSendToNotebook?: (seed: Omit<IncomingNotebookCellSeed, "seq">) => void;
  notebookSummaries?: NotebookSummary[];
  activeNotebookId?: string | null;
}

export function ComputeTester({
  operations,
  onPlotExpression,
  onSendToNotebook,
  notebookSummaries = [],
  activeNotebookId = null,
}: ComputeTesterProps) {
  const exprInputRef = useRef<HTMLInputElement | null>(null);
  const [keypadOpen, setKeypadOpen] = useState(false);
  const [operation, setOperation] = useState("differentiate");
  const [expression, setExpression] = useState("x^3 + 2*x");
  const [variable, setVariable] = useState("x");
  const [assumptions, setAssumptions] = useState<Record<string, string>>({});
  const [options, setOptions] = useState<Record<string, unknown>>({});
  const [optionsDraft, setOptionsDraft] = useState("{}");
  const [loading, setLoading] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [result, setResult] = useState<ComputeResponse | null>(null);
  const [explanation, setExplanation] = useState<AIExplainResponse | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const [sendModalOpen, setSendModalOpen] = useState(false);
  const [sendDestMode, setSendDestMode] = useState<"existing" | "new">("existing");
  const [selectedNotebookId, setSelectedNotebookId] = useState<string>("");
  const [newNotebookTitle, setNewNotebookTitle] = useState("");
  const [newNotebookMode, setNewNotebookMode] = useState<NotebookMode>("computational");

  const op = operation.trim().toLowerCase();
  const isMatrixOp = isMatrixLikeOperation(op);
  const usesVariable = OPS_WITH_VARIABLE.has(op);
  const variableLabel = OP_VAR_LABELS[op] ?? "Variable";

  function syncOptions(nextOptions: Record<string, unknown>) {
    setOptions(nextOptions);
    setOptionsDraft(JSON.stringify(nextOptions, null, 2));
  }

  function updateOptionField(key: string, value: unknown) {
    const next = { ...options };
    if (value === "" || value === undefined || value === null) {
      delete next[key];
    } else {
      next[key] = value;
    }
    syncOptions(next);
  }

  function handleOperationChange(nextOp: string) {
    const cleanNext = nextOp.trim().toLowerCase();
    const isBinaryMatrix = cleanNext === "matrix_add" || cleanNext === "matrix_multiply";
    const isSingleMatrix = cleanNext.startsWith("matrix_") && !isBinaryMatrix;

    let nextOpts = { ...options };
    if (cleanNext === "linear_system_solve") {
      if (!nextOpts.matrix) {
        nextOpts = { matrix: [[2, 1], [1, -1]], vector: [5, 1] };
      } else if (!nextOpts.vector) {
        const rows = normalizeMatrixData(nextOpts.matrix).length;
        nextOpts = { ...nextOpts, vector: normalizeVectorData(undefined, rows) };
      }
    } else if (isBinaryMatrix && (!nextOpts.matrix_a || !nextOpts.matrix_b)) {
      nextOpts = {
        matrix_a: normalizeMatrixData(nextOpts.matrix_a ?? nextOpts.matrix),
        matrix_b: normalizeMatrixData(nextOpts.matrix_b),
      };
    } else if (isSingleMatrix && !nextOpts.matrix) {
      nextOpts = { matrix: normalizeMatrixData(nextOpts.matrix_a) };
    }

    setOperation(nextOp);
    syncOptions(nextOpts);
    setResult(null);
    setExplanation(null);
    setError(null);
  }

  function applyPreset(preset: Preset) {
    setOperation(preset.operation);
    setExpression(preset.expression);
    setVariable(preset.variable || "x");
    syncOptions(preset.options);
    setResult(null);
    setExplanation(null);
    setError(null);
  }

  function handleOptionsJsonChange(rawJson: string) {
    setOptionsDraft(rawJson);
    if (!rawJson.trim()) {
      setOptions({});
      return;
    }
    try {
      const candidate: unknown = JSON.parse(rawJson);
      if (candidate && typeof candidate === "object" && !Array.isArray(candidate)) {
        setError(null);
        setOptions(candidate as Record<string, unknown>);
      }
    } catch {
      /* Keep draft editable until valid JSON is completed */
    }
  }

  function parseValidatedOptions(): Record<string, unknown> | null {
    if (!optionsDraft.trim()) return {};
    try {
      const candidate: unknown = JSON.parse(optionsDraft);
      if (candidate && typeof candidate === "object" && !Array.isArray(candidate)) {
        return candidate as Record<string, unknown>;
      }
      const msg = "Advanced options must be a JSON object.";
      setError({ code: "INVALID_JSON", message: msg });
      showToast(msg, { variant: "error" });
      return null;
    } catch {
      const msg = "Advanced options JSON is malformed.";
      setError({ code: "INVALID_JSON", message: msg });
      showToast(msg, { variant: "error" });
      return null;
    }
  }

  async function executeCompute() {
    setError(null);
    setResult(null);

    const parsedOptions = parseValidatedOptions();
    if (!parsedOptions) return;

    setLoading(true);
    try {
      const response = await runCompute({
        operation,
        expression: !isMatrixOp && expression.trim() ? expression.trim() : null,
        variable: usesVariable && variable.trim() ? variable.trim() : null,
        assumptions: Object.keys(assumptions).length > 0 ? assumptions : null,
        options: parsedOptions,
      });
      setResult(response);
      showToast("Computed successfully", { detail: response.result, variant: "success" });
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({ code: err.code, message: err.message });
        showToast(err.message, { variant: "error" });
      } else {
        const msg = err instanceof Error ? err.message : "Failed to reach backend API.";
        setError({ code: "NETWORK_ERROR", message: msg });
        showToast(msg, { variant: "error" });
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleExplain() {
    if (explanation) {
      setExplanation(null);
      return;
    }
    const parsedOptions = parseValidatedOptions();
    if (!parsedOptions) return;

    setError(null);
    setExplaining(true);
    try {
      const explained = await explainMath({
        operation,
        expression: !isMatrixOp && expression.trim() ? expression.trim() : null,
        variable: usesVariable && variable.trim() ? variable.trim() : null,
        assumptions: Object.keys(assumptions).length > 0 ? assumptions : null,
        options: parsedOptions,
        mode: "learning",
      });
      setExplanation(explained);
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to generate explanation.";
      setError({ code: "EXPLAIN_ERROR", message: msg });
      showToast(msg, { variant: "error" });
    } finally {
      setExplaining(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void executeCompute();
  }

  const availableOps =
    operations.length > 0
      ? operations
      : PRESETS.map((p) => ({
          name: p.operation,
          domain: "math",
          description: p.label,
          aliases: [],
        }));

  const notationPreview = formatCellNotationLatex({
    operation,
    expression,
    variable: usesVariable ? variable : null,
    options,
  });

  const matrixPlotSeed = isMatrixOp
    ? buildMatrixPlotSeed(
        operation,
        options,
        result?.metadata?.details as Record<string, unknown> | undefined
      )
    : null;
  const canPlotExpr = Boolean(onPlotExpression && !isMatrixOp && expression.trim());

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div className="flex flex-wrap gap-2">
        {PRESETS.map((preset) => {
          const isCurrent =
            preset.operation === operation &&
            (!preset.expression || preset.expression === expression);
          return (
            <button
              key={preset.label}
              type="button"
              onClick={() => applyPreset(preset)}
              className={`rounded border px-3 py-1.5 text-xs font-medium transition sm:text-[13px] ${
                isCurrent
                  ? "border-[var(--border-strong)] bg-[var(--bg-subtle)] text-[var(--text-primary)]"
                  : "border-[var(--border-hairline)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
              }`}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-5 sm:p-6"
      >
        <div className={`grid gap-4 ${usesVariable ? "sm:grid-cols-2" : ""}`}>
          <div>
            <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Operation
            </label>
            <select
              value={operation}
              onChange={(e) => handleOperationChange(e.target.value)}
              className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
            >
              {availableOps.map((item) => (
                <option key={item.name} value={item.name}>
                  {formatOperationLabel(item.name)}
                </option>
              ))}
            </select>
          </div>

          {usesVariable && (
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                {variableLabel} <span className="font-normal opacity-75">(optional)</span>
              </label>
              <input
                type="text"
                value={variable}
                onChange={(e) => setVariable(e.target.value)}
                placeholder="auto (e.g. x)"
                className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 font-mono text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none"
              />
            </div>
          )}
        </div>

        {!isMatrixOp ? (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Expression / Equation
              </label>
              <button
                type="button"
                onClick={() => setKeypadOpen((prev) => !prev)}
                className={`rounded border px-2 py-0.5 text-[11px] transition ${
                  keypadOpen
                    ? "border-[var(--border-strong)] bg-[var(--bg-surface)] font-medium text-[var(--text-primary)]"
                    : "border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
                }`}
              >
                {keypadOpen ? "Hide Keypad" : "Keypad"}
              </button>
            </div>
            <input
              ref={exprInputRef}
              type="text"
              value={expression}
              onChange={(e) => setExpression(e.target.value)}
              placeholder="e.g. x^3 + 2*x or x^2 - 5*x + 6 = 0"
              className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 font-mono text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none"
            />
            {notationPreview && (
              <div className="flex items-center gap-2.5 overflow-x-auto rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)]/50 px-3 py-1 text-xs">
                <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                  Notation
                </span>
                <LatexBlock latex={notationPreview} displayMode={false} />
              </div>
            )}
            {keypadOpen && (
              <MathKeypad
                onInsert={(text, cursorBack) =>
                  insertIntoInputElement(
                    exprInputRef.current,
                    expression,
                    text,
                    cursorBack,
                    setExpression
                  )
                }
                onBackspace={() =>
                  backspaceInputElement(exprInputRef.current, expression, setExpression)
                }
                onClear={() => setExpression("")}
                onRun={() => void executeCompute()}
                onClose={() => setKeypadOpen(false)}
              />
            )}
          </div>
        ) : (
          <div className="space-y-2.5">
            <div className="flex flex-wrap items-start gap-3">
              {op === "matrix_add" || op === "matrix_multiply" ? (
                <>
                  <MatrixGridEditor
                    label="Matrix A"
                    value={options.matrix_a ?? options.matrix}
                    onChange={(nextMatrix: MatrixData) =>
                      syncOptions({ ...options, matrix_a: nextMatrix })
                    }
                  />
                  <MatrixGridEditor
                    label="Matrix B"
                    value={options.matrix_b}
                    onChange={(nextMatrix: MatrixData) =>
                      syncOptions({ ...options, matrix_b: nextMatrix })
                    }
                  />
                </>
              ) : op === "linear_system_solve" ? (
                <>
                  <MatrixGridEditor
                    label="Matrix A"
                    value={options.matrix}
                    onChange={(nextMatrix: MatrixData) =>
                      syncOptions({
                        ...options,
                        matrix: nextMatrix,
                        vector: normalizeVectorData(options.vector, nextMatrix.length),
                      })
                    }
                  />
                  <VectorGridEditor
                    label="Vector b"
                    length={normalizeMatrixData(options.matrix).length}
                    value={options.vector}
                    onChange={(nextVec) => syncOptions({ ...options, vector: nextVec })}
                  />
                </>
              ) : (
                <MatrixGridEditor
                  label="Matrix"
                  value={options.matrix}
                  onChange={(nextMatrix: MatrixData) =>
                    syncOptions({ ...options, matrix: nextMatrix })
                  }
                />
              )}
            </div>

            {notationPreview && (
              <div className="flex items-center gap-2.5 overflow-x-auto rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)]/50 px-3 py-1 text-xs">
                <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                  Notation
                </span>
                <LatexBlock latex={notationPreview} displayMode={false} />
              </div>
            )}
          </div>
        )}

        {(op === "integrate" || op === "numerical_integrate") && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Lower Bound <span className="font-normal opacity-75">(optional)</span>
              </label>
              <input
                type="text"
                value={String(options.lower ?? "")}
                onChange={(e) => updateOptionField("lower", e.target.value)}
                placeholder="e.g. 0"
                className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Upper Bound <span className="font-normal opacity-75">(optional)</span>
              </label>
              <input
                type="text"
                value={String(options.upper ?? "")}
                onChange={(e) => updateOptionField("upper", e.target.value)}
                placeholder="e.g. 3"
                className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none"
              />
            </div>
          </div>
        )}

        {(op === "limit" || op === "taylor_series") && (
          <div className={`grid gap-3 ${op === "taylor_series" ? "sm:grid-cols-2" : ""}`}>
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                {op === "limit" ? "Target Point (→)" : "Expansion Point"}
              </label>
              <input
                type="text"
                value={String(options.point ?? "")}
                onChange={(e) => updateOptionField("point", e.target.value)}
                placeholder="0"
                className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none"
              />
            </div>
            {op === "taylor_series" && (
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Order
                </label>
                <input
                  type="number"
                  min={1}
                  max={12}
                  value={Number(options.order ?? 5)}
                  onChange={(e) => updateOptionField("order", Number(e.target.value))}
                  className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 font-mono text-xs text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
                />
              </div>
            )}
          </div>
        )}

        {op === "root_find" && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Bracket Min
              </label>
              <input
                type="number"
                step="any"
                value={Array.isArray(options.bracket) ? String(options.bracket[0] ?? 0) : ""}
                onChange={(e) => {
                  const cur = Array.isArray(options.bracket) ? options.bracket : [0, 2];
                  updateOptionField("bracket", [Number(e.target.value), Number(cur[1] ?? 2)]);
                }}
                placeholder="0"
                className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 font-mono text-xs text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Bracket Max
              </label>
              <input
                type="number"
                step="any"
                value={Array.isArray(options.bracket) ? String(options.bracket[1] ?? 2) : ""}
                onChange={(e) => {
                  const cur = Array.isArray(options.bracket) ? options.bracket : [0, 2];
                  updateOptionField("bracket", [Number(cur[0] ?? 0), Number(e.target.value)]);
                }}
                placeholder="2"
                className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 font-mono text-xs text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
              />
            </div>
          </div>
        )}

        <AssumptionsEditor assumptions={assumptions} onChange={setAssumptions} />

        <details className="pt-0.5">
          <summary className="cursor-pointer select-none font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)] hover:text-[var(--text-primary)]">
            Advanced Options (JSON)
          </summary>
          <textarea
            rows={2}
            value={optionsDraft}
            onChange={(e) => handleOptionsJsonChange(e.target.value)}
            placeholder='e.g. {"lower": 0, "upper": 3} or {"matrix": [[1, 2], [3, 4]]}'
            className="mt-1.5 w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none"
          />
        </details>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border-hairline)] pt-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="submit"
              disabled={loading}
              className="rounded bg-[var(--accent-ink)] px-4 py-1.5 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90 disabled:opacity-60"
            >
              {loading ? "Computing..." : "Compute"}
            </button>
            <button
              type="button"
              onClick={() => void handleExplain()}
              disabled={explaining}
              className={`rounded border px-3 py-1.5 text-xs font-medium transition disabled:opacity-50 ${
                explanation
                  ? "border-[var(--border-strong)] bg-[var(--bg-subtle)] text-[var(--text-primary)]"
                  : "border-[var(--border-hairline)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
              }`}
            >
              {explaining ? "Explaining..." : explanation ? "Hide Guide" : "Explain"}
            </button>
            {onPlotExpression && isMatrixOp && matrixPlotSeed && (
              <button
                type="button"
                onClick={() => onPlotExpression(matrixPlotSeed)}
                className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
              >
                {matrixPlotSeed.matrixB && result ? "Plot Result" : "Plot"}
              </button>
            )}
            {canPlotExpr && (() => {
              const plotExpr = preparePlottableExpression(expression, operation);
              const compareResult = extractPlottableCompareResult(result?.result, plotExpr);
              return (
                <button
                  type="button"
                  onClick={() =>
                    onPlotExpression?.({
                      plotType: "2d",
                      expr: plotExpr,
                      compareExpr: compareResult,
                      variable: usesVariable && variable.trim() ? variable.trim() : undefined,
                    })
                  }
                  className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
                >
                  {compareResult ? "Plot Result" : "Plot"}
                </button>
              );
            })()}
          </div>

          {onSendToNotebook && (
            <button
              type="button"
              onClick={() => {
                const parsedOpts = parseValidatedOptions();
                if (!parsedOpts) return;
                const hasExisting = notebookSummaries.length > 0;
                setSendDestMode(hasExisting ? "existing" : "new");
                setSelectedNotebookId(
                  activeNotebookId || notebookSummaries[0]?.id || ""
                );
                setNewNotebookTitle(`Notebook ${notebookSummaries.length + 1}`);
                setSendModalOpen(true);
              }}
              className="rounded border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] transition hover:bg-[var(--bg-canvas)]"
            >
              + Send to Notebook
            </button>
          )}
        </div>
      </form>

      {error && <ErrorAlert code={error.code} message={error.message} />}

      {result && (
        <div className="space-y-3 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <span className="font-medium text-[var(--text-secondary)]">
              {formatHumanLabel(result.metadata.domain)} · {formatHumanLabel(result.metadata.method)}
            </span>
            <span className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2 py-0.5 text-[11px] font-medium text-[var(--text-secondary)]">
              {formatOperationLabel(result.operation)}
            </span>
          </div>

          <ExplainableOutputPanel
            resultText={result.result}
            resultLatex={result.latex}
            reasoning={result.reasoning}
            verification={result.verification}
          />
        </div>
      )}

      {explanation && (
        <StepByStepGuide
          sourceLabel={
            explanation.explanation_source === "llm_grounded"
              ? "AI Grounded"
              : "Step Walkthrough"
          }
          summary={explanation.summary}
          steps={explanation.steps}
          onClose={() => setExplanation(null)}
        />
      )}

      <Modal
        open={sendModalOpen}
        onClose={() => setSendModalOpen(false)}
        maxWidthClass="max-w-sm"
      >
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">
          Send Cell to Notebook
        </h2>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">
          Choose an existing notebook or create a new one for this{" "}
          <span className="font-medium text-[var(--text-primary)]">
            {formatOperationLabel(operation)}
          </span>{" "}
          cell.
        </p>

        <div className="mt-3 inline-flex w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-0.5 text-xs">
          <button
            type="button"
            disabled={notebookSummaries.length === 0}
            onClick={() => setSendDestMode("existing")}
            className={`flex-1 rounded-sm py-1.5 font-medium transition disabled:opacity-40 ${
              sendDestMode === "existing"
                ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Existing Notebook
          </button>
          <button
            type="button"
            onClick={() => setSendDestMode("new")}
            className={`flex-1 rounded-sm py-1.5 font-medium transition ${
              sendDestMode === "new"
                ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            + Create New
          </button>
        </div>

        {sendDestMode === "existing" && notebookSummaries.length > 0 ? (
          <div className="mt-3">
            <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Target Notebook
            </label>
            <select
              value={selectedNotebookId}
              onChange={(e) => setSelectedNotebookId(e.target.value)}
              className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
            >
              {notebookSummaries.map((nb) => (
                <option key={nb.id} value={nb.id}>
                  {nb.title} ({nb.cell_count} cells{nb.id === activeNotebookId ? " · current" : ""})
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="mt-3 space-y-3">
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                New Notebook Title
              </label>
              <input
                type="text"
                value={newNotebookTitle}
                onChange={(e) => setNewNotebookTitle(e.target.value)}
                placeholder={`Notebook ${notebookSummaries.length + 1}`}
                className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 text-xs text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Mode
              </label>
              <div className="inline-flex w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-0.5 text-xs">
                {(["computational", "learning"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setNewNotebookMode(m)}
                    className={`flex-1 rounded-sm py-1 capitalize transition ${
                      newNotebookMode === m
                        ? "bg-[var(--bg-surface)] font-medium text-[var(--text-primary)] shadow-xs"
                        : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setSendModalOpen(false)}
            className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              const parsedOpts = parseValidatedOptions();
              if (!parsedOpts || !onSendToNotebook) return;
              setSendModalOpen(false);
              onSendToNotebook({
                operation,
                expression: !isMatrixOp && expression.trim() ? expression.trim() : null,
                variable: usesVariable && variable.trim() ? variable.trim() : null,
                assumptions: { ...assumptions },
                options: parsedOpts,
                ...(sendDestMode === "new" || notebookSummaries.length === 0
                  ? {
                      newNotebook: {
                        title:
                          newNotebookTitle.trim() || `Notebook ${notebookSummaries.length + 1}`,
                        mode: newNotebookMode,
                      },
                    }
                  : { targetNotebookId: selectedNotebookId }),
              });
            }}
            className="rounded bg-[var(--accent-ink)] px-3.5 py-1.5 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90"
          >
            {sendDestMode === "new" ? "Create & Send" : "Add to Notebook"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
