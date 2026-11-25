import { FormEvent, useState } from "react";

import { ApiClientError, explainMath } from "../../services/api";
import type { AIExplainResponse, NotebookMode, WorkedExample } from "../../types/compute";
import { StepByStepGuide } from "../common/StepByStepGuide";
import { LatexBlock } from "../computation/LatexBlock";

interface LearningAssistantPanelProps {
  mode: NotebookMode;
  examples: WorkedExample[];
  onInsertCell: (cell: {
    operation: string;
    expression: string | null;
    variable: string | null;
    options: Record<string, unknown>;
  }) => void;
}

export function LearningAssistantPanel({
  mode,
  examples,
  onInsertCell,
}: LearningAssistantPanelProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState<AIExplainResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAsk(e: FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setError(null);
    setLoading(true);
    try {
      const res = await explainMath({ prompt: prompt.trim(), mode });
      setExplanation(res);
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to interpret prompt."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleRunExample(ex: WorkedExample) {
    setError(null);
    setLoading(true);
    try {
      const res = await explainMath({
        prompt: ex.prompt,
        operation: ex.operation,
        expression: ex.expression,
        variable: ex.variable,
        options: ex.options,
        mode,
      });
      setExplanation(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run example.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
            Learning Mode · Guided Walkthrough
          </h3>
          <p className="text-[11px] text-[var(--text-secondary)]">
            Natural-language queries are translated into whitelisted operations and verified.
          </p>
        </div>
        <span className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2 py-0.5 font-mono text-[10px] uppercase text-[var(--text-secondary)]">
          {mode}
        </span>
      </div>

      <form onSubmit={handleAsk} className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. differentiate x^3 + 2*x, or integrate x^2 from 0 to 3"
          className="flex-1 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:bg-[var(--bg-surface)] focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-[var(--accent-ink)] px-3.5 py-1.5 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90 disabled:opacity-60"
        >
          {loading ? "Running..." : "Explain"}
        </button>
      </form>

      {examples.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-[var(--text-muted)]">Worked examples:</span>
          {examples.map((ex) => (
            <button
              key={ex.id}
              type="button"
              onClick={() => void handleRunExample(ex)}
              className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
            >
              {ex.title}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded border border-rose-500/40 bg-rose-500/10 p-2.5 text-xs text-rose-600">
          {error}
        </div>
      )}

      {explanation && (
        <div className="space-y-3 border-t border-[var(--border-hairline)] pt-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2 font-mono text-[var(--text-secondary)]">
              <span>
                {explanation.operation}({explanation.expression ?? "matrix"}) ={" "}
                <span className="font-semibold text-[var(--text-primary)]">
                  {explanation.result}
                </span>
              </span>
              <span className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--text-muted)]">
                {explanation.interpretation_source === "llm_translated"
                  ? "LLM NLP"
                  : explanation.interpretation_source === "deterministic_nlp"
                    ? "Pattern NLP"
                    : "Structured"}{" "}
                ·{" "}
                {explanation.explanation_source === "llm_grounded"
                  ? "LLM Grounded"
                  : "Grounded Steps"}
              </span>
            </div>

            <button
              type="button"
              onClick={() =>
                onInsertCell({
                  operation: explanation.operation,
                  expression: explanation.expression,
                  variable: explanation.variable ?? null,
                  options: explanation.options ?? {},
                })
              }
              className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1 text-[11px] font-medium text-[var(--text-primary)] hover:border-[var(--border-strong)]"
            >
              + Insert Cell
            </button>
          </div>

          <LatexBlock latex={explanation.latex} displayMode={false} />
          <StepByStepGuide
            sourceLabel={
              explanation.explanation_source === "llm_grounded"
                ? "AI Grounded"
                : "Step Walkthrough"
            }
            summary={explanation.summary}
            steps={explanation.steps}
          />
        </div>
      )}
    </div>
  );
}
