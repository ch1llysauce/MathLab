import katex from "katex";
import { Fragment } from "react";

interface ExplanationStep {
  title: string;
  content: string;
}

interface StepByStepGuideProps {
  title?: string;
  sourceLabel?: string;
  summary: string;
  steps: ExplanationStep[];
  onClose?: () => void;
}

const MATH_TOKEN_RE = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|\$(?!\s)[^$\n]+?(?<!\s)\$)/g;

/** Renders mixed prose and inline/display LaTeX delimiters via KaTeX. */
function MathText({ text }: { text: string }) {
  const parts = text.split(MATH_TOKEN_RE);

  return (
    <>
      {parts.map((part, idx) => {
        if (!part) return null;
        let tex: string | null = null;
        let displayMode = false;

        if (part.startsWith("$$") && part.endsWith("$$") && part.length > 4) {
          tex = part.slice(2, -2).trim();
          displayMode = true;
        } else if (part.startsWith("\\[") && part.endsWith("\\]") && part.length > 4) {
          tex = part.slice(2, -2).trim();
          displayMode = true;
        } else if (part.startsWith("\\(") && part.endsWith("\\)") && part.length > 4) {
          tex = part.slice(2, -2).trim();
        } else if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
          tex = part.slice(1, -1).trim();
        }

        if (tex === null) {
          return <Fragment key={idx}>{part}</Fragment>;
        }

        try {
          const html = katex.renderToString(tex, {
            displayMode,
            throwOnError: false,
            strict: false,
          });
          return (
            <span
              key={idx}
              className={displayMode ? "my-1 block overflow-x-auto" : "inline-block align-baseline"}
              dangerouslySetInnerHTML={{ __html: html }}
            />
          );
        } catch {
          return <Fragment key={idx}>{part}</Fragment>;
        }
      })}
    </>
  );
}

export function StepByStepGuide({
  title = "Step-by-Step Solution",
  sourceLabel,
  summary,
  steps,
  onClose,
}: StepByStepGuideProps) {
  return (
    <div className="space-y-3 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-3.5 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            {title}
          </span>
          {sourceLabel && (
            <span className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-muted)]">
              {sourceLabel}
            </span>
          )}
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            Close
          </button>
        )}
      </div>

      {steps.length > 0 && (
        <ol className="space-y-2">
          {steps.map((step, idx) => (
            <li
              key={idx}
              className="flex gap-2.5 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-2"
            >
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-[var(--border-strong)] bg-[var(--bg-subtle)] font-mono text-[10px] font-semibold text-[var(--text-primary)]">
                {idx + 1}
              </span>
              <div className="min-w-0 space-y-0.5">
                <div className="font-semibold text-[var(--text-primary)]">{step.title}</div>
                <p className="text-[11px] leading-relaxed text-[var(--text-secondary)]">
                  <MathText text={step.content} />
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}

      {summary && (
        <div className="rounded border-l-2 border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 py-2">
          <div className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Why this result
          </div>
          <p className="mt-0.5 text-[11px] leading-relaxed text-[var(--text-primary)]">
            <MathText text={summary} />
          </p>
        </div>
      )}
    </div>
  );
}
