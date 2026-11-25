import { useState } from "react";

import type { ReasoningAnalysis, VerificationResult } from "../../types/compute";
import { formatHumanLabel } from "../../utils/operationLabels";
import { showToast } from "../common/Toast";
import { LatexBlock } from "./LatexBlock";

interface ExplainableOutputPanelProps {
  resultText: string;
  resultLatex: string;
  reasoning?: ReasoningAnalysis | null;
  verification?: VerificationResult | null;
  learningMode?: boolean;
}

const VERIFICATION_STYLES: Record<VerificationResult["status"], string> = {
  verified: "border-emerald-500/35 bg-emerald-500/10 text-[var(--status-verified)]",
  numerical_support: "border-sky-500/35 bg-sky-500/10 text-[var(--status-info)]",
  partial: "border-amber-500/35 bg-amber-500/10 text-[var(--status-warn)]",
  inconclusive: "border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[var(--text-secondary)]",
};

function humanizeTechnicalText(text: string): string {
  return text
    .replace(/'([a-z0-9]+(?:_[a-z0-9]+)+)'/gi, (_m, tok: string) =>
      `"${tok.replace(/_/g, " ")}"`
    )
    .replace(/\b([a-z0-9]+(?:_[a-z0-9]+)+)\b/gi, (tok) => tok.replace(/_/g, " "))
    .replace(
      /because all required applicability conditions passed/gi,
      "because all mathematical conditions for this method are met"
    )
    .replace(
      /SymPy treats undeclared symbols as general complex\/symbolic unless restricted/gi,
      "variables without explicit assumptions can represent any real or complex number"
    )
    .replace(/;\s*max residual = 0\.0+e\+00/gi, " (all values matched exactly, difference = 0)")
    .replace(/\b0\.0+e\+00\b/gi, "0");
}

export function ExplainableOutputPanel({
  resultText,
  resultLatex,
  reasoning,
  verification,
}: ExplainableOutputPanelProps) {
  const [copied, setCopied] = useState(false);
  const status = verification?.status ?? "inconclusive";
  const badgeClass = VERIFICATION_STYLES[status];

  async function handleCopyResult() {
    try {
      await navigator.clipboard.writeText(resultText);
      setCopied(true);
      showToast("Copied to clipboard", { detail: resultText, variant: "success" });
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      showToast("Could not access clipboard", { variant: "error" });
    }
  }

  return (
    <div className="space-y-2.5 border-l-2 border-[var(--border-strong)] pl-3.5 pt-0.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="font-mono text-[11px] text-[var(--text-muted)]">
          Out: <code className="text-[var(--text-secondary)]">{resultText}</code>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => void handleCopyResult()}
            title="Copy raw result"
            className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-muted)] transition hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
          >
            {copied ? "Copied" : "Copy"}
          </button>

          {verification && (
            <span
              className={`rounded border px-1.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wide ${badgeClass}`}
              title={verification.summary}
            >
              {verification.status}
            </span>
          )}
        </div>
      </div>

      <LatexBlock latex={resultLatex} />

      {(reasoning || verification) && (
        <details className="pt-1 text-xs">
          <summary className="cursor-pointer select-none font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
            Reasoning, Assumptions &amp; Verification
          </summary>

          <div className="mt-2.5 grid gap-2 text-[var(--text-secondary)] sm:grid-cols-2">
            {reasoning && (
              <>
                <div className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-2.5">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    1. Problem &amp; Method
                  </div>
                  <p className="mt-1 font-medium text-[var(--text-primary)]">
                    {formatHumanLabel(reasoning.classification.problem_type)} →{" "}
                    {formatHumanLabel(reasoning.selection.recommended_method)}
                  </p>
                  <p className="mt-1 text-[11px] leading-relaxed">
                    {humanizeTechnicalText(reasoning.selection.rationale)}
                  </p>
                </div>

                <div className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-2.5">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    2. Domain &amp; Assumptions
                  </div>
                  {reasoning.assumptions.constraints.length > 0 ? (
                    <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[11px]">
                      {reasoning.assumptions.constraints.map((c, idx) => (
                        <li key={idx}>
                          <code className="text-[var(--text-primary)]">{c.condition}</code> —{" "}
                          {humanizeTechnicalText(c.reason)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-[11px] leading-relaxed">
                      No restricted values (such as division by zero) detected.{" "}
                      {humanizeTechnicalText(reasoning.assumptions.notes.join(" "))}
                    </p>
                  )}
                </div>
              </>
            )}

            {verification && (
              <div className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-2.5 sm:col-span-2">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  3. Result Verification ({formatHumanLabel(verification.status)})
                </div>
                <p className="mt-1 text-[11px] text-[var(--text-primary)]">
                  {humanizeTechnicalText(verification.summary)}
                </p>
                {verification.checks.length > 0 && (
                  <ul className="mt-1.5 space-y-1 text-[11px]">
                    {verification.checks.map((chk, idx) => (
                      <li key={idx} className="flex flex-wrap items-baseline gap-1.5">
                        <span
                          className={
                            chk.passed === true
                              ? "rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-[var(--status-verified)]"
                              : chk.passed === false
                                ? "rounded bg-rose-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-[var(--status-error)]"
                                : "rounded bg-[var(--bg-surface)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-muted)]"
                          }
                        >
                          {chk.passed === true ? "Passed" : chk.passed === false ? "Failed" : "Note"}
                        </span>
                        <span className="font-medium text-[var(--text-primary)]">
                          {formatHumanLabel(chk.name)}:
                        </span>
                        <span>{humanizeTechnicalText(chk.message)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </details>
      )}
    </div>
  );
}
