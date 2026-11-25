import { useState } from "react";

const SUPPORTED_ASSUMPTIONS = [
  "real",
  "positive",
  "negative",
  "nonnegative",
  "integer",
  "complex",
] as const;

interface AssumptionsEditorProps {
  assumptions: Record<string, string>;
  onChange: (next: Record<string, string>) => void;
  compact?: boolean;
}

export function AssumptionsEditor({
  assumptions,
  onChange,
  compact = false,
}: AssumptionsEditorProps) {
  const [symbol, setSymbol] = useState("x");
  const [domain, setDomain] = useState<(typeof SUPPORTED_ASSUMPTIONS)[number]>("real");

  function handleAdd() {
    const cleanSym = symbol.trim();
    if (!/^[a-zA-Z][a-zA-Z0-9_]{0,15}$/.test(cleanSym)) return;
    onChange({ ...assumptions, [cleanSym]: domain });
  }

  function handleRemove(key: string) {
    const next = { ...assumptions };
    delete next[key];
    onChange(next);
  }

  const entries = Object.entries(assumptions);

  return (
    <div className={compact ? "space-y-1.5" : "space-y-2"}>
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="font-mono text-[10px] uppercase text-[var(--text-muted)]">
          Assumptions:
        </span>
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="symbol"
          className="w-16 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
        />
        <select
          value={domain}
          onChange={(e) =>
            setDomain(e.target.value as (typeof SUPPORTED_ASSUMPTIONS)[number])
          }
          className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--text-primary)] focus:outline-none"
        >
          {SUPPORTED_ASSUMPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleAdd}
          className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 py-0.5 text-[11px] font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
        >
          + Add
        </button>
      </div>

      {entries.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {entries.map(([sym, val]) => (
            <span
              key={sym}
              className="inline-flex items-center gap-1 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 py-0.5 font-mono text-[11px] text-[var(--text-secondary)]"
            >
              <strong className="text-[var(--text-primary)]">{sym}</strong>: {val}
              <button
                type="button"
                onClick={() => handleRemove(sym)}
                aria-label={`Remove assumption for ${sym}`}
                className="ml-0.5 text-[var(--text-muted)] hover:text-rose-600"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
