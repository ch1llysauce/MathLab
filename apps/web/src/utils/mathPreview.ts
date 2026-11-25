/**
 * Lightweight presentation-only ASCII math -> KaTeX LaTeX formatter and input cursor helpers.
 * Never performs mathematical evaluation; all computation stays on the Python backend.
 */

function findClosingParen(text: string, openIdx: number): number {
  let depth = 0;
  for (let i = openIdx; i < text.length; i++) {
    if (text[i] === "(") depth++;
    else if (text[i] === ")") {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

function replaceFunctionCall(
  input: string,
  fnName: string,
  wrap: (inner: string) => string
): string {
  const re = new RegExp(`\\b${fnName}\\(`, "i");
  let out = input;
  let guard = 0;
  while (guard < 24) {
    guard++;
    const match = re.exec(out);
    if (!match) break;
    const openIdx = match.index + fnName.length;
    const closeIdx = findClosingParen(out, openIdx);
    if (closeIdx === -1) break;
    const inner = out.slice(openIdx + 1, closeIdx);
    const formattedInner = transformCore(inner);
    out = `${out.slice(0, match.index)}${wrap(formattedInner)}${out.slice(closeIdx + 1)}`;
  }
  return out;
}

function replaceSimpleFractions(text: string): string {
  return text.replace(
    /(\([^()]+\)|\\sqrt\{[^{}]+\}|[a-zA-Z0-9^_{}]+)\s*\/\s*(\([^()]+\)|\\sqrt\{[^{}]+\}|[a-zA-Z0-9^_{}]+)/g,
    (_m, num: string, den: string) => {
      const cleanNum = num.startsWith("(") && num.endsWith(")") ? num.slice(1, -1) : num;
      const cleanDen = den.startsWith("(") && den.endsWith(")") ? den.slice(1, -1) : den;
      return `\\frac{${cleanNum}}{${cleanDen}}`;
    }
  );
}

function transformCore(raw: string): string {
  let s = raw.trim();
  if (!s) return "";

  s = replaceFunctionCall(s, "sqrt", (inner) => `\\sqrt{${inner}}`);
  s = replaceFunctionCall(s, "abs", (inner) => `\\left|${inner}\\right|`);
  s = replaceFunctionCall(s, "exp", (inner) => `e^{${inner}}`);

  s = s.replace(/\bpi\b/gi, "\\pi ");
  s = s.replace(/\b(?:oo|inf)\b/gi, "\\infty ");

  s = s.replace(/\^\(([^()]+)\)/g, "^{$1}");
  s = s.replace(/\^([a-zA-Z0-9]+)/g, "^{$1}");

  s = s.replace(
    /\b(sin|cos|tan|csc|sec|cot|asin|acos|atan|sinh|cosh|tanh|ln|log)\b/gi,
    (fn) => `\\${fn.toLowerCase()}`
  );

  s = replaceSimpleFractions(s);
  s = s.replace(/\s*\*\s*/g, " \\cdot ");

  return s;
}

function matrixToLatex(raw: unknown): string | null {
  if (!Array.isArray(raw) || raw.length === 0 || !Array.isArray(raw[0])) {
    return null;
  }
  const rows = raw
    .map((row) =>
      Array.isArray(row) ? row.map((cell) => transformCore(String(cell)) || "0").join(" & ") : ""
    )
    .filter(Boolean);
  if (rows.length === 0) return null;
  return `\\begin{bmatrix} ${rows.join(" \\\\ ")} \\end{bmatrix}`;
}

function vectorToLatex(raw: unknown): string | null {
  if (!Array.isArray(raw) || raw.length === 0) return null;
  const rows = raw.map((val) => transformCore(String(val)) || "0");
  return `\\begin{bmatrix} ${rows.join(" \\\\ ")} \\end{bmatrix}`;
}

export function formatAsciiMathPreview(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const hasFormattingTokens =
    /[\^/*()]|\b(?:sqrt|pi|oo|inf|sin|cos|tan|ln|log|exp|abs)\b/i.test(trimmed);
  if (!hasFormattingTokens) return null;
  return transformCore(trimmed);
}

const RESERVED_PREVIEW_SYMBOLS = new Set([
  "e", "i", "pi", "oo", "inf",
  "sin", "cos", "tan", "csc", "sec", "cot",
  "asin", "acos", "atan", "sinh", "cosh", "tanh",
  "ln", "log", "exp", "sqrt", "abs",
]);

function extractPreviewVariables(expr: string): string[] {
  const found = new Set<string>();
  for (const match of expr.matchAll(/\b([a-zA-Z][a-zA-Z0-9_]*)\b/g)) {
    const token = match[1];
    if (!RESERVED_PREVIEW_SYMBOLS.has(token.toLowerCase())) {
      found.add(token);
    }
  }
  return [...found];
}

export function formatCellNotationLatex(params: {
  operation: string;
  expression?: string | null;
  variable?: string | null;
  assignTo?: string | null;
  options?: Record<string, unknown>;
}): string | null {
  const op = (params.operation || "simplify").trim().toLowerCase();
  const opts = params.options || {};
  let exprRaw = (params.expression || "").trim();
  let inlineAssign: string | null = null;

  if (op !== "assign" && op !== "solve" && op !== "solve_ode" && op !== "root_find") {
    const explicitVar = params.variable?.trim() || "";
    const eqMatch = /^([a-zA-Z][a-zA-Z0-9_]{0,15})\s*=\s*(.+)$/.exec(exprRaw);
    if (eqMatch && !/^(?:e|i|pi|oo|inf)$/i.test(eqMatch[1]) && eqMatch[1] !== explicitVar) {
      inlineAssign = eqMatch[1];
      exprRaw = eqMatch[2].trim();
    }
  }

  const detectedVars = extractPreviewVariables(exprRaw);
  const hasAmbiguousSolveVars =
    op === "solve" && !params.variable?.trim() && detectedVars.length > 1;
  const varName =
    params.variable?.trim() ||
    (detectedVars.length === 1 ? detectedVars[0] : "x");

  const exprLatex = exprRaw ? transformCore(exprRaw) : "\\square";
  const effectiveAssign = params.assignTo?.trim() || inlineAssign;
  const prefix = effectiveAssign ? `${effectiveAssign} = ` : "";

  if (op === "matrix_add" || op === "matrix_multiply") {
    const aLatex = matrixToLatex(opts.matrix_a ?? opts.matrix);
    const bLatex = matrixToLatex(opts.matrix_b);
    if (!aLatex && !bLatex) return null;
    const sym = op === "matrix_add" ? "+" : "\\times";
    return `${prefix}${aLatex ?? "A"} ${sym} ${bLatex ?? "B"}`;
  }

  if (op === "linear_system_solve") {
    const aLatex = matrixToLatex(opts.matrix);
    const bLatex = vectorToLatex(opts.vector);
    if (!aLatex) return null;
    return `${prefix}${aLatex} \\mathbf{x} = ${bLatex ?? "\\mathbf{b}"}`;
  }

  if (op.startsWith("matrix_")) {
    const mLatex = matrixToLatex(opts.matrix);
    if (!mLatex) return null;
    if (op === "matrix_determinant") return `${prefix}\\det ${mLatex}`;
    if (op === "matrix_inverse") return `${prefix}${mLatex}^{-1}`;
    if (op === "matrix_transpose") return `${prefix}${mLatex}^{\\mathsf{T}}`;
    if (op === "matrix_rank") return `${prefix}\\operatorname{rank}${mLatex}`;
    if (op === "matrix_rref") return `${prefix}\\operatorname{RREF}${mLatex}`;
    if (op === "matrix_eigenvalues") return `${prefix}\\operatorname{eigvals}${mLatex}`;
    if (op === "matrix_eigenvectors") return `${prefix}\\operatorname{eigvecs}${mLatex}`;
    return `${prefix}${mLatex}`;
  }

  if (op === "assign") {
    return exprRaw ? transformCore(exprRaw) : null;
  }

  if (op === "differentiate") {
    return `${prefix}\\frac{d}{d${varName}}\\left( ${exprLatex} \\right)`;
  }

  if (op === "partial_derivative") {
    return `${prefix}\\frac{\\partial}{\\partial ${varName}}\\left( ${exprLatex} \\right)`;
  }

  if (op === "integrate" || op === "numerical_integrate") {
    const lower = opts.lower !== undefined && String(opts.lower).trim() !== "" ? transformCore(String(opts.lower)) : "";
    const upper = opts.upper !== undefined && String(opts.upper).trim() !== "" ? transformCore(String(opts.upper)) : "";
    if (lower !== "" || upper !== "") {
      return `${prefix}\\int_{${lower || "a"}}^{${upper || "b"}} \\left( ${exprLatex} \\right)\\, d${varName}`;
    }
    return `${prefix}\\int \\left( ${exprLatex} \\right)\\, d${varName}`;
  }

  if (op === "limit") {
    const pt = opts.point !== undefined && String(opts.point).trim() !== "" ? transformCore(String(opts.point)) : "0";
    return `${prefix}\\lim_{${varName} \\to ${pt}} \\left( ${exprLatex} \\right)`;
  }

  if (op === "taylor_series") {
    const pt = opts.point !== undefined && String(opts.point).trim() !== "" ? transformCore(String(opts.point)) : "0";
    const order = opts.order ?? 5;
    return `${prefix}T_{${order}}\\left( ${exprLatex} \\right)\\Big|_{${varName}=${pt}}`;
  }

  if (op === "solve") {
    const rhsAware = exprRaw.includes("=") ? exprLatex : `${exprLatex} = 0`;
    if (hasAmbiguousSolveVars) {
      return `${prefix}\\text{Solve (choose variable)}:\\; ${rhsAware}`;
    }
    return `${prefix}\\text{Solve for } ${varName}:\\; ${rhsAware}`;
  }

  if (op === "solve_ode") {
    return `${prefix}\\text{ODE: } ${exprLatex}`;
  }

  if (op === "root_find") {
    const bracket = Array.isArray(opts.bracket) ? `[${opts.bracket[0] ?? "a"}, ${opts.bracket[1] ?? "b"}]` : "";
    return `${prefix}\\text{Root of } ${exprLatex} = 0${bracket ? `\\;\\text{on } ${bracket}` : ""}`;
  }

  if (!exprRaw) return null;
  if (op === "factor" || op === "expand" || op === "simplify") {
    return `${prefix}\\operatorname{${op}}\\left( ${exprLatex} \\right)`;
  }
  return `${prefix}${exprLatex}`;
}

function coreExprToPlotlyHtml(raw: string): string {
  let s = raw.trim();
  if (!s) return "";

  // Convert explicit multiplication and symbols to clean typographic math for Plotly SVG spans.
  s = s.replace(/\*\*/g, "^");
  s = s.replace(/\bpi\b/gi, "π");
  s = s.replace(/\b(?:oo|inf)\b/gi, "∞");
  s = s.replace(/\bsqrt\(/gi, "√(");

  // Exponents: ^(expr) or ^token -> <sup>...</sup> (non-nested for Plotly SVG compatibility).
  s = s.replace(/\^\(([^()]+)\)/g, (_m, exp: string) => `<sup>${exp.trim()}</sup>`);
  s = s.replace(/\^([a-zA-Z0-9]+)/g, (_m, exp: string) => `<sup>${exp}</sup>`);

  // Implicit-friendly multiplication: digit*letter -> 2x, letter*letter -> x·y
  s = s.replace(/(\d)\s*\*\s*([a-zA-Z(√π])/g, "$1$2");
  s = s.replace(/\s*\*\s*/g, " · ");

  // Binary minus with spaces -> true minus sign
  s = s.replace(/\s+-\s+/g, " − ");

  // Italicize single-letter variables outside HTML tags and function names.
  const fnNames = new Set([
    "sin", "cos", "tan", "csc", "sec", "cot",
    "asin", "acos", "atan", "sinh", "cosh", "tanh",
    "ln", "log", "exp", "abs",
  ]);
  s = s.replace(/(<[^>]+>)|(\b[a-zA-Z][a-zA-Z0-9_]*\b)/g, (_match, tag: string, word: string) => {
    if (tag) return tag;
    if (fnNames.has(word.toLowerCase())) return word;
    if (word.length === 1) return `<i>${word}</i>`;
    const subMatch = /^([a-zA-Z])(\d+)$/.exec(word);
    if (subMatch) return `<i>${subMatch[1]}</i><sub>${subMatch[2]}</sub>`;
    return word;
  });

  return s;
}

/** Formats Plotly chart titles (possibly comma-separated expressions) into SVG math markup. */
export function formatPlotlyTitleHtml(title: string): string {
  if (/(?:Linear|Matrix|Heatmap|Planes|Vectors|Surface|Projection)/i.test(title)) {
    return title;
  }
  return title
    .split(",")
    .map((part) => coreExprToPlotlyHtml(part))
    .filter(Boolean)
    .join(", ");
}

/** Formats backend trace names (curves, derivatives, tangents, integrals) into Plotly SVG math markup. */
export function formatPlotlyTraceName(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return name;

  const derivMatch = /^(d\/d([a-zA-Z]\w*)|∂f\/∂([a-zA-Z]\w*)):\s*(.+)$/.exec(trimmed);
  if (derivMatch) {
    const prefixRaw = derivMatch[1];
    const exprHtml = coreExprToPlotlyHtml(derivMatch[4]);
    if (prefixRaw.startsWith("d/d")) {
      return `<i>d</i>/<i>d</i><i>${derivMatch[2]}</i>: ${exprHtml}`;
    }
    return `∂<i>f</i>/∂<i>${derivMatch[3]}</i>: ${exprHtml}`;
  }

  if (trimmed.startsWith("Area under ")) {
    return `Area under ${coreExprToPlotlyHtml(trimmed.slice("Area under ".length))}`;
  }

  const fnEqMatch = /^f(\d+)\(([^)]+)\)\s*=\s*(.+)$/.exec(trimmed);
  if (fnEqMatch) {
    const argsHtml = fnEqMatch[2]
      .split(",")
      .map((v) => `<i>${v.trim()}</i>`)
      .join(", ");
    return `<i>f</i><sub>${fnEqMatch[1]}</sub>(${argsHtml}) = ${coreExprToPlotlyHtml(fnEqMatch[3])}`;
  }

  const tanLine2d = /^Tangent at ([a-zA-Z]\w*)=([^\s(]+)\s+\(slope=([^)]+)\)$/.exec(trimmed);
  if (tanLine2d) {
    return `Tangent at <i>${tanLine2d[1]}</i> = ${tanLine2d[2]} (slope = ${tanLine2d[3]})`;
  }

  const tanDir3d = /^Tangent ∂([a-zA-Z]\w*)\s+\(slope=([^)]+)\)$/.exec(trimmed);
  if (tanDir3d) {
    return `Tangent ∂<i>${tanDir3d[1]}</i> (slope = ${tanDir3d[2]})`;
  }

  if (
    trimmed === "Key Points" ||
    trimmed === "Matrix Values" ||
    trimmed === "Matrix Entries" ||
    trimmed === "Unit Square" ||
    trimmed === "Unit Cube" ||
    trimmed.startsWith("Transformed ") ||
    trimmed.startsWith("Result / Compare") ||
    trimmed.startsWith("Eigenvector") ||
    trimmed.startsWith("Solution (") ||
    trimmed.startsWith("A·e") ||
    trimmed.startsWith("B·e") ||
    trimmed.startsWith("Eq ") ||
    trimmed.startsWith("Tangent Plane") ||
    trimmed.startsWith("Tangent Point") ||
    trimmed.endsWith("Height Surface")
  ) {
    return trimmed;
  }

  return coreExprToPlotlyHtml(trimmed);
}

export function insertIntoInputElement(
  el: HTMLInputElement | null,
  currentValue: string,
  text: string,
  cursorBack = 0,
  onUpdate?: (next: string) => void
): string {
  if (!el) {
    const next = `${currentValue}${text}`;
    onUpdate?.(next);
    return next;
  }
  const start = el.selectionStart ?? currentValue.length;
  const end = el.selectionEnd ?? currentValue.length;
  const next = `${currentValue.slice(0, start)}${text}${currentValue.slice(end)}`;
  const nextCursor = Math.max(0, start + text.length - cursorBack);
  onUpdate?.(next);
  requestAnimationFrame(() => {
    el.focus();
    el.setSelectionRange(nextCursor, nextCursor);
  });
  return next;
}

export function backspaceInputElement(
  el: HTMLInputElement | null,
  currentValue: string,
  onUpdate?: (next: string) => void
): string {
  if (!el) {
    const next = currentValue.slice(0, -1);
    onUpdate?.(next);
    return next;
  }
  const start = el.selectionStart ?? currentValue.length;
  const end = el.selectionEnd ?? currentValue.length;
  if (start === 0 && end === 0) return currentValue;
  const next =
    start !== end
      ? `${currentValue.slice(0, start)}${currentValue.slice(end)}`
      : `${currentValue.slice(0, start - 1)}${currentValue.slice(end)}`;
  const nextCursor = start !== end ? start : Math.max(0, start - 1);
  onUpdate?.(next);
  requestAnimationFrame(() => {
    el.focus();
    el.setSelectionRange(nextCursor, nextCursor);
  });
  return next;
}
