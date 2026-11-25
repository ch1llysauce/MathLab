import type {
  CellInput,
  NotebookCell,
  NotebookMode,
  NotebookResponse,
  NotebookSummary,
} from "../types/compute";

const GUEST_STORAGE_KEY = "mathlab_guest_notebooks_v1";

function nowIso(): string {
  return new Date().toISOString();
}

function readAll(): NotebookResponse[] {
  try {
    const raw = window.localStorage.getItem(GUEST_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as NotebookResponse[]) : [];
  } catch {
    return [];
  }
}

function writeAll(notebooks: NotebookResponse[]): void {
  const sorted = [...notebooks].sort((a, b) =>
    b.updated_at.localeCompare(a.updated_at)
  );
  window.localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(sorted));
}

function cellSignature(cell: Pick<CellInput, "cell_type" | "operation" | "expression" | "variable" | "assign_to" | "assumptions" | "options">): string {
  return JSON.stringify({
    cell_type: cell.cell_type,
    operation: cell.operation ?? null,
    expression: cell.expression ?? null,
    variable: cell.variable ?? null,
    assign_to: cell.assign_to ?? null,
    assumptions: cell.assumptions ?? {},
    options: cell.options ?? {},
  });
}

function toNotebookCells(
  notebookId: string,
  inputs: CellInput[],
  existingCells: NotebookCell[] = []
): NotebookCell[] {
  const existingById = new Map(existingCells.map((c) => [c.id, c]));
  const invalidatedIds = new Set<string>();

  return inputs.map((input, idx) => {
    const id = input.id || crypto.randomUUID();
    const prev = existingById.get(id);
    const unchanged = prev ? cellSignature(prev) === cellSignature(input) : false;
    const upstreamDirty = prev
      ? prev.depends_on.some((depId) => invalidatedIds.has(depId))
      : false;

    if (prev && unchanged && !upstreamDirty) {
      return {
        ...prev,
        notebook_id: notebookId,
        position: idx,
      };
    }

    invalidatedIds.add(id);

    return {
      id,
      notebook_id: notebookId,
      position: idx,
      cell_type: input.cell_type,
      operation: input.operation ?? null,
      expression: input.expression ?? null,
      variable: input.variable ?? null,
      assign_to: input.assign_to ?? null,
      assumptions: { ...(input.assumptions ?? {}) },
      options: { ...(input.options ?? {}) },
      status: input.cell_type === "math" ? (prev?.result ? "stale" : "idle") : "valid",
      depends_on: prev?.depends_on ?? [],
      error_message: null,
      result: prev && input.cell_type === "math" ? prev.result : null,
    };
  });
}

export function listGuestNotebooks(): NotebookSummary[] {
  return readAll().map((nb) => ({
    id: nb.id,
    title: nb.title,
    mode: nb.mode,
    cell_count: nb.cells.length,
    created_at: nb.created_at,
    updated_at: nb.updated_at,
  }));
}

export function listRawGuestNotebooks(): NotebookResponse[] {
  return readAll();
}

export function getGuestNotebook(notebookId: string): NotebookResponse | null {
  return readAll().find((nb) => nb.id === notebookId) ?? null;
}

export function createGuestNotebook(payload: {
  title: string;
  mode: NotebookMode;
  cells: CellInput[];
}): NotebookResponse {
  const id = crypto.randomUUID();
  const timestamp = nowIso();
  const created: NotebookResponse = {
    id,
    title: payload.title,
    mode: payload.mode,
    created_at: timestamp,
    updated_at: timestamp,
    cells: toNotebookCells(id, payload.cells),
    variables: {},
  };
  writeAll([created, ...readAll()]);
  return created;
}

export function updateGuestNotebook(
  notebookId: string,
  payload: { title?: string; mode?: NotebookMode; cells?: CellInput[] }
): NotebookResponse {
  const all = readAll();
  const existing = all.find((nb) => nb.id === notebookId);
  if (!existing) {
    throw new Error("Guest notebook was not found in browser storage.");
  }

  const updated: NotebookResponse = {
    ...existing,
    title: payload.title ?? existing.title,
    mode: payload.mode ?? existing.mode,
    updated_at: nowIso(),
    cells: payload.cells
      ? toNotebookCells(notebookId, payload.cells, existing.cells)
      : existing.cells,
  };

  writeAll(all.map((nb) => (nb.id === notebookId ? updated : nb)));
  return updated;
}

export function saveGuestNotebookSnapshot(notebook: NotebookResponse): NotebookResponse {
  const all = readAll();
  const exists = all.some((nb) => nb.id === notebook.id);
  const next = exists
    ? all.map((nb) => (nb.id === notebook.id ? notebook : nb))
    : [notebook, ...all];
  writeAll(next);
  return notebook;
}

export function deleteGuestNotebook(notebookId: string): void {
  writeAll(readAll().filter((nb) => nb.id !== notebookId));
}

export function clearGuestNotebooks(): void {
  window.localStorage.removeItem(GUEST_STORAGE_KEY);
}

export function exportGuestNotebook(
  nb: NotebookResponse,
  format: "markdown" | "json" = "markdown"
): { filename: string; media_type: string; content: string } {
  const safeSlug =
    nb.title
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, "_")
      .replace(/^_+|_+$/g, "") || "notebook";

  if (format === "json") {
    return {
      filename: `${safeSlug}.json`,
      media_type: "application/json",
      content: JSON.stringify(nb, null, 2),
    };
  }

  const lines: string[] = [
    `# ${nb.title}`,
    "",
    `- **Mode:** \`${nb.mode}\``,
    `- **Updated:** \`${nb.updated_at}\``,
    "",
  ];

  const varEntries = Object.entries(nb.variables);
  if (varEntries.length > 0) {
    lines.push("## Active Variables", "");
    for (const [sym, binding] of varEntries) {
      lines.push(`- \`${sym} = ${binding.value_expr}\` (\`$$${binding.value_latex}$$\`)`);
    }
    lines.push("");
  }

  lines.push("## Cells", "");
  nb.cells.forEach((cell, idx) => {
    const opLabel = cell.operation || cell.cell_type;
    lines.push(`### Cell ${idx + 1} · \`${opLabel}\` (${cell.status})`, "");
    if (cell.expression) {
      lines.push(`Input: \`${cell.expression}\``, "");
    }
    if (cell.error_message) {
      lines.push(`> **Error:** ${cell.error_message}`, "");
    }
    if (cell.result) {
      lines.push(`Output: \`${cell.result.result_text}\``, "");
      lines.push(`$$ ${cell.result.result_latex} $$`, "");
      if (cell.result.verification) {
        const vStatus = String(cell.result.verification.status ?? "inconclusive");
        const vSummary = String(cell.result.verification.summary ?? "");
        lines.push(`- **Verification:** \`${vStatus}\` — ${vSummary}`, "");
      }
    }
  });

  return {
    filename: `${safeSlug}.md`,
    media_type: "text/markdown",
    content: `${lines.join("\n").trim()}\n`,
  };
}
