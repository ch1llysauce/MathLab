import { FormEvent, useState } from "react";

import { ApiClientError, runCompute } from "../../services/api";
import type { ComputeResponse, OperationInfo } from "../../types/compute";
import { LatexBlock } from "./LatexBlock";

interface Preset {
  label: string;
  operation: string;
  expression: string;
  variable: string;
  optionsJson: string;
}

const PRESETS: Preset[] = [
  {
    label: "Differentiate",
    operation: "differentiate",
    expression: "x^3 + 2*x",
    variable: "x",
    optionsJson: "{}",
  },
  {
    label: "Integrate",
    operation: "integrate",
    expression: "2*x",
    variable: "x",
    optionsJson: "{}",
  },
  {
    label: "Solve Equation",
    operation: "solve",
    expression: "x^2 - 5*x + 6 = 0",
    variable: "x",
    optionsJson: "{}",
  },
  {
    label: "Limit",
    operation: "limit",
    expression: "sin(x)/x",
    variable: "x",
    optionsJson: '{"point": 0}',
  },
  {
    label: "Matrix Eigenvalues",
    operation: "matrix_eigenvalues",
    expression: "",
    variable: "",
    optionsJson: '{"matrix": [[2, 0], [0, 3]]}',
  },
  {
    label: "Root Find",
    operation: "root_find",
    expression: "x^2 - 2",
    variable: "x",
    optionsJson: '{"bracket": [1, 2]}',
  },
];

interface ComputeTesterProps {
  operations: OperationInfo[];
}

export function ComputeTester({ operations }: ComputeTesterProps) {
  const [operation, setOperation] = useState("differentiate");
  const [expression, setExpression] = useState("x^3 + 2*x");
  const [variable, setVariable] = useState("x");
  const [optionsJson, setOptionsJson] = useState("{}");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ComputeResponse | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);

  const isMatrixOp = operation.startsWith("matrix_");

  function applyPreset(preset: Preset) {
    setOperation(preset.operation);
    setExpression(preset.expression);
    setVariable(preset.variable);
    setOptionsJson(preset.optionsJson);
    setError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);

    let parsedOptions: Record<string, unknown> = {};
    if (optionsJson.trim()) {
      try {
        const candidate: unknown = JSON.parse(optionsJson);
        if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
          setError({ code: "INVALID_JSON", message: "Options must be a JSON object." });
          return;
        }
        parsedOptions = candidate as Record<string, unknown>;
      } catch {
        setError({ code: "INVALID_JSON", message: "Options JSON is malformed." });
        return;
      }
    }

    setLoading(true);
    try {
      const response = await runCompute({
        operation,
        expression: expression.trim() ? expression.trim() : null,
        variable: variable.trim() ? variable.trim() : null,
        options: parsedOptions,
      });
      setResult(response);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({ code: err.code, message: err.message });
      } else {
        setError({
          code: "NETWORK_ERROR",
          message: err instanceof Error ? err.message : "Failed to reach backend API.",
        });
      }
    } finally {
      setLoading(false);
    }
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

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {PRESETS.map((preset) => (
          <button
            key={preset.label}
            type="button"
            onClick={() => applyPreset(preset)}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-indigo-400 hover:bg-slate-800"
          >
            {preset.label}
          </button>
        ))}
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/70 p-5"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Operation
            </label>
            <select
              value={operation}
              onChange={(e) => setOperation(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
            >
              {availableOps.map((op) => (
                <option key={op.name} value={op.name}>
                  {op.name} ({op.domain})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Variable (optional)
            </label>
            <input
              type="text"
              value={variable}
              onChange={(e) => setVariable(e.target.value)}
              placeholder="e.g. x"
              disabled={isMatrixOp}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
            />
          </div>
        </div>

        {!isMatrixOp && (
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Expression / Equation
            </label>
            <input
              type="text"
              value={expression}
              onChange={(e) => setExpression(e.target.value)}
              placeholder="e.g. x^3 + 2*x or x^2 - 5*x + 6 = 0"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
        )}

        <div>
          <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">
            Options (JSON)
          </label>
          <textarea
            rows={3}
            value={optionsJson}
            onChange={(e) => setOptionsJson(e.target.value)}
            placeholder='e.g. {"lower": 0, "upper": 3} or {"matrix": [[1, 2], [3, 4]]}'
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Computing..." : "Compute"}
        </button>
      </form>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-sm text-rose-200">
          <div className="font-mono text-xs font-semibold uppercase text-rose-400">{error.code}</div>
          <p className="mt-1">{error.message}</p>
        </div>
      )}

      {result && (
        <div className="space-y-4 rounded-xl border border-emerald-500/30 bg-slate-900/80 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-emerald-400">
              Result ({result.metadata.domain} / {result.metadata.method})
            </span>
            <span className="rounded-md bg-slate-800 px-2 py-0.5 font-mono text-xs text-slate-300">
              {result.operation}
            </span>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
            <div className="text-xs text-slate-400">Rendered (KaTeX)</div>
            <LatexBlock latex={result.latex} />
            <div className="mt-3 border-t border-slate-800 pt-2 text-xs text-slate-400">
              Plain Output: <code className="font-mono text-slate-200">{result.result}</code>
            </div>
          </div>

          <details className="text-xs text-slate-400">
            <summary className="cursor-pointer font-medium text-slate-300 hover:text-white">
              Raw Metadata Details
            </summary>
            <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-950 p-3 font-mono text-slate-300">
              {JSON.stringify(result.metadata.details, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
