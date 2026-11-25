interface MathKeypadProps {
  onInsert: (text: string, cursorBack?: number) => void;
  onBackspace: () => void;
  onClear: () => void;
  onRun?: () => void;
  onClose?: () => void;
}

interface KeyDef {
  label: string;
  insert: string;
  cursorBack?: number;
  title?: string;
}

const SYMBOL_AND_FN_KEYS: KeyDef[] = [
  { label: "x", insert: "x" },
  { label: "y", insert: "y" },
  { label: "t", insert: "t" },
  { label: "π", insert: "pi", title: "pi (π)" },
  { label: "e", insert: "e" },
  { label: "∞", insert: "oo", title: "Infinity (oo)" },
  { label: "x²", insert: "^2", title: "Square (^2)" },
  { label: "xⁿ", insert: "^", title: "Power (^)" },
  { label: "√", insert: "sqrt()", cursorBack: 1, title: "Square root" },
  { label: "|x|", insert: "abs()", cursorBack: 1, title: "Absolute value" },
  { label: "sin", insert: "sin()", cursorBack: 1 },
  { label: "cos", insert: "cos()", cursorBack: 1 },
  { label: "tan", insert: "tan()", cursorBack: 1 },
  { label: "ln", insert: "ln()", cursorBack: 1 },
  { label: "log", insert: "log()", cursorBack: 1 },
  { label: "eˣ", insert: "exp()", cursorBack: 1, title: "Exponential exp()" },
];

const CORE_PAD_ROWS: Array<Array<KeyDef | "BACKSPACE" | "CLEAR" | "RUN">> = [
  [
    { label: "7", insert: "7" },
    { label: "8", insert: "8" },
    { label: "9", insert: "9" },
    { label: "÷", insert: "/", title: "Divide (/)" },
    { label: "(", insert: "(" },
    { label: ")", insert: ")" },
    "BACKSPACE",
  ],
  [
    { label: "4", insert: "4" },
    { label: "5", insert: "5" },
    { label: "6", insert: "6" },
    { label: "×", insert: "*", title: "Multiply (*)" },
    { label: "^", insert: "^" },
    { label: "=", insert: " = " },
    "CLEAR",
  ],
  [
    { label: "1", insert: "1" },
    { label: "2", insert: "2" },
    { label: "3", insert: "3" },
    { label: "−", insert: "-" },
    { label: "0", insert: "0" },
    { label: ".", insert: "." },
    { label: "+", insert: "+" },
  ],
];

const KEY_BTN_CLASS =
  "rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 py-1.5 font-mono text-xs font-medium text-[var(--text-primary)] transition hover:border-[var(--border-strong)] hover:bg-[var(--bg-canvas)] active:scale-[0.98]";

export function MathKeypad({
  onInsert,
  onBackspace,
  onClear,
  onRun,
  onClose,
}: MathKeypadProps) {
  return (
    <div className="space-y-2 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-2.5">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Math Keypad
        </span>
        {onClose && (
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={onClose}
            className="text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            Hide
          </button>
        )}
      </div>

      {/* Variables, Constants & Functions */}
      <div className="grid grid-cols-8 gap-1 sm:grid-cols-8">
        {SYMBOL_AND_FN_KEYS.map((item) => (
          <button
            key={item.label}
            type="button"
            title={item.title ?? item.insert}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => onInsert(item.insert, item.cursorBack)}
            className={KEY_BTN_CLASS}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Numbers & Core Operators */}
      <div className="space-y-1">
        {CORE_PAD_ROWS.map((row, rowIdx) => (
          <div key={rowIdx} className="grid grid-cols-7 gap-1">
            {row.map((cell) => {
              if (cell === "BACKSPACE") {
                return (
                  <button
                    key="backspace"
                    type="button"
                    title="Backspace"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={onBackspace}
                    className={`${KEY_BTN_CLASS} text-[var(--text-secondary)]`}
                  >
                    ⌫
                  </button>
                );
              }
              if (cell === "CLEAR") {
                return (
                  <button
                    key="clear"
                    type="button"
                    title="Clear expression"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={onClear}
                    className={`${KEY_BTN_CLASS} text-[11px] text-[var(--status-error)]`}
                  >
                    Clear
                  </button>
                );
              }
              if (cell === "RUN") return null;
              return (
                <button
                  key={cell.label}
                  type="button"
                  title={cell.title ?? cell.insert}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => onInsert(cell.insert, cell.cursorBack)}
                  className={KEY_BTN_CLASS}
                >
                  {cell.label}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {onRun && (
        <div className="flex justify-end pt-0.5">
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={onRun}
            className="rounded bg-[var(--accent-ink)] px-3 py-1 text-[11px] font-semibold text-[var(--accent-ink-fg)] hover:opacity-90"
          >
            Run ↵
          </button>
        </div>
      )}
    </div>
  );
}
