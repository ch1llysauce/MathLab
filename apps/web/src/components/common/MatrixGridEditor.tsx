type CellVal = number | string;
export type MatrixData = CellVal[][];

function parseMatrixCell(raw: string): CellVal {
  const trimmed = raw.trim();
  if (trimmed === "") return 0;
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
    return Number(trimmed);
  }
  return trimmed;
}

export function normalizeMatrixData(raw: unknown, fallbackRows = 2, fallbackCols = 2): MatrixData {
  if (Array.isArray(raw) && raw.length > 0 && Array.isArray(raw[0])) {
    const rows = raw.map((r) =>
      Array.isArray(r) ? r.map((c) => (typeof c === "number" || typeof c === "string" ? c : 0)) : []
    );
    const maxCols = Math.max(...rows.map((r) => r.length), 1);
    return rows.map((r) => {
      const padded = [...r];
      while (padded.length < maxCols) padded.push(0);
      return padded;
    });
  }
  return Array.from({ length: fallbackRows }, (_, r) =>
    Array.from({ length: fallbackCols }, (_, c) => (r === c ? 1 : 0))
  );
}

export function normalizeVectorData(raw: unknown, length: number): CellVal[] {
  const base = Array.isArray(raw)
    ? raw.map((v) => (typeof v === "number" || typeof v === "string" ? v : 0))
    : [];
  const next = [...base];
  while (next.length < length) next.push(0);
  return next.slice(0, Math.max(length, 1));
}

interface MatrixGridEditorProps {
  label: string;
  value: unknown;
  onChange: (next: MatrixData) => void;
}

export function MatrixGridEditor({ label, value, onChange }: MatrixGridEditorProps) {
  const matrix = normalizeMatrixData(value);
  const rowCount = matrix.length;
  const colCount = matrix[0]?.length ?? 2;

  function updateCell(r: number, c: number, raw: string) {
    const next = matrix.map((row, rIdx) =>
      row.map((val, cIdx) => (rIdx === r && cIdx === c ? parseMatrixCell(raw) : val))
    );
    onChange(next);
  }

  function resize(nextRows: number, nextCols: number) {
    const boundedRows = Math.max(1, Math.min(6, nextRows));
    const boundedCols = Math.max(1, Math.min(6, nextCols));
    const next: MatrixData = Array.from({ length: boundedRows }, (_, r) =>
      Array.from({ length: boundedCols }, (_, c) => matrix[r]?.[c] ?? 0)
    );
    onChange(next);
  }

  return (
    <div className="space-y-1.5 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)]/60 p-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
        <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
          {label} ({rowCount}×{colCount})
        </span>
        <div className="flex items-center gap-2 font-mono text-[10px] text-[var(--text-muted)]">
          <span>Rows:</span>
          <button
            type="button"
            onClick={() => resize(rowCount - 1, colCount)}
            disabled={rowCount <= 1}
            className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.2 hover:text-[var(--text-primary)] disabled:opacity-40"
          >
            -
          </button>
          <button
            type="button"
            onClick={() => resize(rowCount + 1, colCount)}
            disabled={rowCount >= 6}
            className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.2 hover:text-[var(--text-primary)] disabled:opacity-40"
          >
            +
          </button>
          <span className="ml-1">Cols:</span>
          <button
            type="button"
            onClick={() => resize(rowCount, colCount - 1)}
            disabled={colCount <= 1}
            className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.2 hover:text-[var(--text-primary)] disabled:opacity-40"
          >
            -
          </button>
          <button
            type="button"
            onClick={() => resize(rowCount, colCount + 1)}
            disabled={colCount >= 6}
            className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.2 hover:text-[var(--text-primary)] disabled:opacity-40"
          >
            +
          </button>
        </div>
      </div>

      <div
        className="grid gap-1.5"
        style={{ gridTemplateColumns: `repeat(${colCount}, minmax(44px, 72px))` }}
      >
        {matrix.map((row, r) =>
          row.map((val, c) => (
            <input
              key={`${r}-${c}`}
              type="text"
              value={String(val)}
              onChange={(e) => updateCell(r, c, e.target.value)}
              aria-label={`${label} row ${r + 1} col ${c + 1}`}
              className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 py-1 text-center font-mono text-xs text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
            />
          ))
        )}
      </div>
    </div>
  );
}

interface VectorGridEditorProps {
  label: string;
  length: number;
  value: unknown;
  onChange: (next: CellVal[]) => void;
}

export function VectorGridEditor({ label, length, value, onChange }: VectorGridEditorProps) {
  const vector = normalizeVectorData(value, length);

  function updateEntry(idx: number, raw: string) {
    const next = vector.map((v, i) => (i === idx ? parseMatrixCell(raw) : v));
    onChange(next);
  }

  return (
    <div className="space-y-1.5 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)]/60 p-2.5">
      <div className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
        {label} ({vector.length}×1)
      </div>
      <div className="flex flex-col gap-1.5">
        {vector.map((val, idx) => (
          <input
            key={idx}
            type="text"
            value={String(val)}
            onChange={(e) => updateEntry(idx, e.target.value)}
            aria-label={`${label} entry ${idx + 1}`}
            className="w-16 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 py-1 text-center font-mono text-xs text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
          />
        ))}
      </div>
    </div>
  );
}
