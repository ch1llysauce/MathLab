import { type DragEvent, useCallback, useEffect, useRef, useState } from "react";

import {
  ApiClientError,
  createNotebook,
  deleteNotebook,
  executeNotebook,
  executeStatelessNotebook,
  explainMath,
  exportNotebook,
  getNotebook,
  listNotebookHistory,
  listNotebooks,
  listWorkedExamples,
  updateNotebook,
} from "../../services/api";
import {
  clearGuestNotebooks,
  createGuestNotebook,
  deleteGuestNotebook,
  exportGuestNotebook,
  getGuestNotebook,
  listGuestNotebooks,
  listRawGuestNotebooks,
  saveGuestNotebookSnapshot,
  updateGuestNotebook,
} from "../../services/guestNotebookStorage";
import type {
  AIExplainResponse,
  CellInput,
  NotebookCell,
  NotebookHistoryEntry,
  NotebookMode,
  NotebookResponse,
  NotebookSummary,
  OperationInfo,
  PlotSeed,
  WorkedExample,
} from "../../types/compute";
import { AssumptionsEditor } from "../common/AssumptionsEditor";
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
import { ExplainableOutputPanel } from "../computation/ExplainableOutputPanel";
import { LatexBlock } from "../computation/LatexBlock";
import { LearningAssistantPanel } from "../learning/LearningAssistantPanel";
import { formatCellNotationLatex } from "../../utils/mathPreview";
import {
  buildMatrixPlotSeed,
  extractPlottableCompareResult,
  formatOperationLabel,
  OP_VAR_LABELS,
  OPS_WITH_VARIABLE,
  preparePlottableExpression,
} from "../../utils/operationLabels";
import { CodeMirrorCellEditor, type CodeMirrorEditorHandle } from "./CodeMirrorCellEditor";

export interface IncomingNotebookCellSeed {
  operation: string;
  expression: string | null;
  variable: string | null;
  assumptions?: Record<string, string>;
  options: Record<string, unknown>;
  targetNotebookId?: string;
  newNotebook?: { title: string; mode: NotebookMode };
  seq: number;
}

interface NotebookWorkbenchProps {
  operations: OperationInfo[];
  authKey: string;
  isAuthenticated: boolean;
  onPlotExpression: (seed: Omit<PlotSeed, "seq">) => void;
  incomingCellSeed?: IncomingNotebookCellSeed;
  onNotebookContextChange?: (summaries: NotebookSummary[], activeId: string | null) => void;
}

const STATUS_DOT: Record<NotebookCell["status"], string> = {
  valid: "bg-emerald-500",
  stale: "bg-amber-500",
  error: "bg-rose-500",
  idle: "bg-zinc-400",
};

const STATUS_LABEL: Record<NotebookCell["status"], string> = {
  valid: "valid",
  stale: "outdated",
  error: "error",
  idle: "ready",
};

const CELL_ACTION_BTN =
  "rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1 text-[var(--text-secondary)] transition hover:border-[var(--border-strong)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)] disabled:opacity-40";
const CELL_ACTION_ACTIVE_BTN =
  "rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-2.5 py-1 font-medium text-[var(--text-primary)] shadow-xs transition";

const OP_PLACEHOLDERS: Record<string, string> = {
  assign: "Bind a symbol, e.g. f = x^3 + 2*x (Shift+Enter to run)",
  solve: "Equation to solve, e.g. x^2 - 5*x + 6 = 0 (Shift+Enter to run)",
  differentiate: "Expression or symbol to differentiate, e.g. x^3 + 2*x or f",
  integrate: "Integrand expression, e.g. x^2 (set bounds in Options for definite integral)",
  limit: "Expression for limit, e.g. (x^2 - 1)/(x - 1) (set point in Options)",
  partial_derivative: "Multivariable expression, e.g. x^2*y + sin(y)",
  taylor_series: "Function to expand, e.g. sin(x) (set point & order in Options)",
  solve_ode: "ODE equation, e.g. y'(x) + y(x) = exp(-x)",
  root_find: "Expression f(x) to find root, e.g. cos(x) - x (set bracket in Options)",
  numerical_integrate: "Integrand expression, e.g. exp(-x^2) (set lower & upper in Options)",
};

function toCellInputs(cells: NotebookCell[]): CellInput[] {
  return cells.map((c) => ({
    id: c.id,
    cell_type: c.cell_type,
    operation: c.operation,
    expression: c.expression,
    variable: c.variable,
    assign_to: c.assign_to,
    assumptions: c.assumptions,
    options: c.options,
  }));
}

function triggerFileDownload(filename: string, mediaType: string, content: string) {
  const blob = new Blob([content], { type: mediaType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function stripInlineAssignForOp(raw: string, operation: string | null | undefined): string {
  const op = (operation ?? "simplify").trim().toLowerCase();
  if (op === "solve" || op === "solve_ode" || op === "root_find") {
    return raw;
  }
  return raw.replace(/^[a-zA-Z][a-zA-Z0-9_]{0,15}\s*=\s*/, "").trim();
}

function renderMarkdownLines(text: string) {
  const lines = text.split(/\r?\n/);
  return lines.map((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return <div key={idx} className="h-2" />;
    }
    if (trimmed.startsWith("### ")) {
      return (
        <h4 key={idx} className="text-xs font-semibold text-[var(--text-primary)]">
          {trimmed.slice(4)}
        </h4>
      );
    }
    if (trimmed.startsWith("## ") || trimmed.startsWith("# ")) {
      const content = trimmed.replace(/^#{1,2}\s+/, "");
      return (
        <h3 key={idx} className="text-sm font-semibold text-[var(--text-primary)]">
          {content}
        </h3>
      );
    }
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      return (
        <div key={idx} className="flex gap-2 text-xs text-[var(--text-secondary)]">
          <span className="text-[var(--text-muted)]">•</span>
          <span>{trimmed.slice(2)}</span>
        </div>
      );
    }
    return (
      <p key={idx} className="text-xs leading-relaxed text-[var(--text-secondary)]">
        {trimmed}
      </p>
    );
  });
}

export function NotebookWorkbench({
  operations,
  authKey,
  isAuthenticated,
  onPlotExpression,
  incomingCellSeed,
  onNotebookContextChange,
}: NotebookWorkbenchProps) {
  const [summaries, setSummaries] = useState<NotebookSummary[]>([]);
  const [activeNb, setActiveNb] = useState<NotebookResponse | null>(null);
  const lastHandledSeedSeq = useRef<number>(0);
  const [examples, setExamples] = useState<WorkedExample[]>([]);
  const editorRefs = useRef<Record<string, CodeMirrorEditorHandle | null>>({});
  const [keypadCellId, setKeypadCellId] = useState<string | null>(null);
  const [dragSourceIdx, setDragSourceIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);
  const [openOptionsCellIds, setOpenOptionsCellIds] = useState<Record<string, boolean>>({});
  const [optionsDrafts, setOptionsDrafts] = useState<Record<string, string>>({});
  const [guestPendingCount, setGuestPendingCount] = useState(0);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [pendingLeaveAction, setPendingLeaveAction] = useState<
    { type: "select"; notebookId: string } | { type: "create" } | null
  >(null);
  const [cellExplanations, setCellExplanations] = useState<Record<string, AIExplainResponse>>({});
  const [explainingCellId, setExplainingCellId] = useState<string | null>(null);
  const [editingMarkdownIds, setEditingMarkdownIds] = useState<Record<string, boolean>>({});
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyEntries, setHistoryEntries] = useState<NotebookHistoryEntry[]>([]);
  const [dirty, setDirty] = useState(false);
  const [justSaved, setJustSaved] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    setError(null);
    setLoadingList(true);
    try {
      const exs = await listWorkedExamples().catch(() => [] as WorkedExample[]);
      setExamples(exs);

      if (!isAuthenticated) {
        const guestList = listGuestNotebooks();
        setSummaries(guestList);
        setGuestPendingCount(0);
        setActiveNb(guestList.length > 0 ? getGuestNotebook(guestList[0].id) : null);
        setOptionsDrafts({});
        setDirty(false);
        return;
      }

      const list = await listNotebooks();
      setSummaries(list);
      setGuestPendingCount(listGuestNotebooks().length);
      if (list.length > 0) {
        const first = await getNotebook(list[0].id);
        setActiveNb(first);
      } else {
        setActiveNb(null);
      }
      setOptionsDrafts({});
      setDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load notebooks.");
    } finally {
      setLoadingList(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    void loadList();
  }, [loadList, authKey]);

  async function performSelectNotebook(id: string) {
    setError(null);
    setBusy(true);
    try {
      const nb = isAuthenticated ? await getNotebook(id) : getGuestNotebook(id);
      if (!nb) {
        throw new Error("Notebook was not found.");
      }
      setActiveNb(nb);
      setOptionsDrafts({});
      setDirty(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load notebook.";
      setError(msg);
      showToast(msg, { variant: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function performCreateNotebook() {
    setError(null);
    setBusy(true);
    const payload = {
      title: `Notebook ${summaries.length + 1}`,
      mode: "computational" as NotebookMode,
      cells: [
        { cell_type: "math" as const, operation: "assign", expression: "f = x^3 + 2*x" },
        { cell_type: "math" as const, operation: "differentiate", expression: "f", variable: "x" },
      ],
    };
    try {
      if (!isAuthenticated) {
        const created = createGuestNotebook(payload);
        setActiveNb(created);
        setOptionsDrafts({});
        setDirty(false);
        setSummaries(listGuestNotebooks());
        showToast("Notebook created", { detail: created.title, variant: "success" });
        return;
      }

      const created = await createNotebook(payload);
      setActiveNb(created);
      setOptionsDrafts({});
      setDirty(false);
      setSummaries(await listNotebooks());
      showToast("Notebook created", { detail: created.title, variant: "success" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create notebook.";
      setError(msg);
      showToast(msg, { variant: "error" });
    } finally {
      setBusy(false);
    }
  }

  function handleSelectNotebook(id: string) {
    if (activeNb?.id === id) return;
    if (dirty) {
      setPendingLeaveAction({ type: "select", notebookId: id });
      return;
    }
    void performSelectNotebook(id);
  }

  function handleCreateNotebook() {
    if (dirty) {
      setPendingLeaveAction({ type: "create" });
      return;
    }
    void performCreateNotebook();
  }

  async function runPendingLeaveAction(
    action: { type: "select"; notebookId: string } | { type: "create" }
  ) {
    if (action.type === "select") {
      await performSelectNotebook(action.notebookId);
    } else {
      await performCreateNotebook();
    }
  }

  async function handleDeleteActiveNotebook() {
    if (!activeNb) return;
    const deletedTitle = activeNb.title;
    setError(null);
    setBusy(true);
    try {
      if (!isAuthenticated) {
        deleteGuestNotebook(activeNb.id);
        const list = listGuestNotebooks();
        setSummaries(list);
        setActiveNb(list.length > 0 ? getGuestNotebook(list[0].id) : null);
        setOptionsDrafts({});
        setDirty(false);
        setConfirmDeleteOpen(false);
        showToast("Notebook deleted", { detail: deletedTitle, variant: "info" });
        return;
      }

      await deleteNotebook(activeNb.id);
      const list = await listNotebooks();
      setSummaries(list);
      if (list.length > 0) {
        setActiveNb(await getNotebook(list[0].id));
      } else {
        setActiveNb(null);
      }
      setOptionsDrafts({});
      setDirty(false);
      setConfirmDeleteOpen(false);
      showToast("Notebook deleted", { detail: deletedTitle, variant: "info" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to delete notebook.";
      setError(msg);
      showToast(msg, { variant: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function handleImportGuestNotebooks() {
    if (!isAuthenticated) return;
    const guestNotebooks = listRawGuestNotebooks();
    if (guestNotebooks.length === 0) return;

    setError(null);
    setBusy(true);
    try {
      let lastCreated: NotebookResponse | null = null;
      for (const guestNb of guestNotebooks) {
        lastCreated = await createNotebook({
          title: guestNb.title,
          mode: guestNb.mode,
          cells: toCellInputs(guestNb.cells),
        });
      }
      clearGuestNotebooks();
      setGuestPendingCount(0);
      const list = await listNotebooks();
      setSummaries(list);
      if (lastCreated) {
        setActiveNb(lastCreated);
      }
      setOptionsDrafts({});
      setDirty(false);
      showToast("Imported to Cloud", {
        detail: `${guestNotebooks.length} notebook${guestNotebooks.length > 1 ? "s" : ""}`,
        variant: "success",
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to import guest notebooks.";
      setError(msg);
      showToast(msg, { variant: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(format: "markdown" | "json") {
    if (!activeNb) return;
    setError(null);
    try {
      const exported = isAuthenticated
        ? await exportNotebook(activeNb.id, format)
        : exportGuestNotebook(activeNb, format);
      triggerFileDownload(exported.filename, exported.media_type, exported.content);
      showToast("Exported notebook", { detail: exported.filename, variant: "success" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to export notebook.";
      setError(msg);
      showToast(msg, { variant: "error" });
    }
  }

  function updateLocalCell(cellId: string, patch: Partial<NotebookCell>) {
    if (!activeNb) return;
    setActiveNb({
      ...activeNb,
      cells: activeNb.cells.map((c) => (c.id === cellId ? { ...c, ...patch } : c)),
    });
    setDirty(true);
  }

  function updateCellOptionField(cell: NotebookCell, key: string, value: unknown) {
    const nextOptions = { ...(cell.options || {}) };
    if (value === "" || value === undefined || value === null) {
      delete nextOptions[key];
    } else {
      nextOptions[key] = value;
    }
    updateLocalCell(cell.id, { options: nextOptions });
    setOptionsDrafts((prev) => ({ ...prev, [cell.id]: JSON.stringify(nextOptions, null, 2) }));
  }

  function handleOptionsJsonChange(cellId: string, rawJson: string) {
    setOptionsDrafts((prev) => ({ ...prev, [cellId]: rawJson }));
    if (!rawJson.trim()) {
      updateLocalCell(cellId, { options: {} });
      return;
    }
    try {
      const parsed: unknown = JSON.parse(rawJson);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        setError(null);
        updateLocalCell(cellId, { options: parsed as Record<string, unknown> });
      }
    } catch {
      /* Keep draft editable until valid JSON is completed */
    }
  }

  function toggleOptionsPanel(cell: NotebookCell) {
    const nextOpen = !openOptionsCellIds[cell.id];
    setOpenOptionsCellIds((prev) => ({ ...prev, [cell.id]: nextOpen }));
    if (nextOpen && optionsDrafts[cell.id] === undefined) {
      setOptionsDrafts((prev) => ({
        ...prev,
        [cell.id]: JSON.stringify(cell.options || {}, null, 2),
      }));
    }
  }

  function handleAddCell(prefill?: {
    operation: string;
    expression: string | null;
    variable: string | null;
    assumptions?: Record<string, string>;
    options: Record<string, unknown>;
  }) {
    if (!activeNb) return;
    const tempId = crypto.randomUUID();
    const nextCell: NotebookCell = {
      id: tempId,
      notebook_id: activeNb.id,
      position: activeNb.cells.length,
      cell_type: "math",
      operation: prefill?.operation ?? "simplify",
      expression: prefill ? prefill.expression : "x^2 + 2*x + 1",
      variable: prefill?.variable ?? null,
      assign_to: null,
      assumptions: prefill?.assumptions ?? {},
      options: prefill?.options ?? {},
      status: "idle",
      depends_on: [],
      error_message: null,
      result: null,
    };
    setActiveNb({
      ...activeNb,
      cells: [...activeNb.cells, nextCell],
    });
    setDirty(true);
  }

  useEffect(() => {
    onNotebookContextChange?.(summaries, activeNb?.id ?? null);
  }, [summaries, activeNb?.id, onNotebookContextChange]);

  useEffect(() => {
    if (!incomingCellSeed || incomingCellSeed.seq === lastHandledSeedSeq.current) return;
    lastHandledSeedSeq.current = incomingCellSeed.seq;

    const newCellInput: CellInput = {
      cell_type: "math",
      operation: incomingCellSeed.operation,
      expression: incomingCellSeed.expression,
      variable: incomingCellSeed.variable,
      assumptions: incomingCellSeed.assumptions ?? {},
      options: incomingCellSeed.options,
    };

    if (incomingCellSeed.newNotebook) {
      const { title, mode } = incomingCellSeed.newNotebook;
      const cleanTitle = title.trim() || `Notebook ${summaries.length + 1}`;
      void (async () => {
        setBusy(true);
        try {
          const payload = { title: cleanTitle, mode, cells: [newCellInput] };
          const created = isAuthenticated
            ? await createNotebook(payload)
            : createGuestNotebook(payload);
          const nextSummaries = isAuthenticated ? await listNotebooks() : listGuestNotebooks();
          setSummaries(nextSummaries);
          if (!dirty) {
            setActiveNb(created);
            setOptionsDrafts({});
            setDirty(false);
          }
          showToast("Created notebook with cell", {
            detail: dirty ? `${created.title} (unsaved draft kept open)` : created.title,
            variant: "success",
          });
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Failed to create notebook.";
          setError(msg);
          showToast(msg, { variant: "error" });
        } finally {
          setBusy(false);
        }
      })();
      return;
    }

    const targetId = incomingCellSeed.targetNotebookId ?? activeNb?.id;
    if (!targetId) {
      showToast("Create or select a notebook first", { variant: "info" });
      return;
    }

    if (activeNb && targetId === activeNb.id) {
      const tempId = crypto.randomUUID();
      const appended: NotebookCell = {
        id: tempId,
        notebook_id: activeNb.id,
        position: activeNb.cells.length,
        cell_type: "math",
        operation: incomingCellSeed.operation,
        expression: incomingCellSeed.expression,
        variable: incomingCellSeed.variable,
        assign_to: null,
        assumptions: incomingCellSeed.assumptions ?? {},
        options: incomingCellSeed.options,
        status: "idle",
        depends_on: [],
        error_message: null,
        result: null,
      };
      setActiveNb((prev) =>
        prev
          ? {
              ...prev,
              cells: [...prev.cells, { ...appended, position: prev.cells.length }],
            }
          : prev
      );
      setDirty(true);
      showToast("Added cell to notebook", { detail: activeNb.title, variant: "success" });
      return;
    }

    void (async () => {
      setBusy(true);
      try {
        const targetNb = isAuthenticated ? await getNotebook(targetId) : getGuestNotebook(targetId);
        if (!targetNb) {
          throw new Error("Target notebook was not found.");
        }
        const payload = {
          title: targetNb.title,
          mode: targetNb.mode,
          cells: [...toCellInputs(targetNb.cells), newCellInput],
        };
        const updated = isAuthenticated
          ? await updateNotebook(targetNb.id, payload)
          : updateGuestNotebook(targetNb.id, payload);
        setSummaries(isAuthenticated ? await listNotebooks() : listGuestNotebooks());
        if (!dirty) {
          setActiveNb(updated);
          setOptionsDrafts({});
          setDirty(false);
        }
        showToast("Added cell to notebook", {
          detail: dirty ? `${updated.title} (unsaved draft kept open)` : updated.title,
          variant: "success",
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to add cell to notebook.";
        setError(msg);
        showToast(msg, { variant: "error" });
      } finally {
        setBusy(false);
      }
    })();
  }, [incomingCellSeed, activeNb, dirty, isAuthenticated, summaries.length]);

  function handleAddMarkdownCell() {
    if (!activeNb) return;
    const tempId = crypto.randomUUID();
    const nextCell: NotebookCell = {
      id: tempId,
      notebook_id: activeNb.id,
      position: activeNb.cells.length,
      cell_type: "markdown",
      operation: null,
      expression: "## Note\nDocument your derivation steps or assumptions here.",
      variable: null,
      assign_to: null,
      assumptions: {},
      options: {},
      status: "valid",
      depends_on: [],
      error_message: null,
      result: null,
    };
    setActiveNb({
      ...activeNb,
      cells: [...activeNb.cells, nextCell],
    });
    setEditingMarkdownIds((prev) => ({ ...prev, [tempId]: true }));
    setDirty(true);
  }

  async function handleOpenHistory() {
    if (!activeNb || !isAuthenticated) return;
    setHistoryOpen(true);
    setHistoryLoading(true);
    setError(null);
    try {
      const entries = await listNotebookHistory(activeNb.id);
      setHistoryEntries(entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load execution history.");
    } finally {
      setHistoryLoading(false);
    }
  }

  function handleRestoreHistory(entry: NotebookHistoryEntry) {
    if (!entry.notebook) return;
    setActiveNb(entry.notebook);
    setOptionsDrafts({});
    setHistoryOpen(false);
    setDirty(true);
    showToast("Snapshot restored", { variant: "info" });
  }

  async function handleExplainCell(cell: NotebookCell) {
    if (!activeNb) return;
    if (cellExplanations[cell.id]) {
      setCellExplanations((prev) => {
        const next = { ...prev };
        delete next[cell.id];
        return next;
      });
      return;
    }

    setError(null);
    setExplainingCellId(cell.id);
    try {
      const raw = (cell.expression ?? "").trim();
      const stripped = raw ? stripInlineAssignForOp(raw, cell.operation) : "";
      const resolvedExpr = stripped ? (activeNb.variables[stripped]?.value_expr ?? stripped) : null;
      const explained = await explainMath({
        operation: cell.operation ?? "simplify",
        expression: resolvedExpr,
        variable: cell.variable,
        assumptions:
          Object.keys(cell.assumptions || {}).length > 0 ? cell.assumptions : null,
        options: cell.options || {},
        mode: "learning",
      });
      setCellExplanations((prev) => ({ ...prev, [cell.id]: explained }));
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to generate explanation for cell.";
      setError(msg);
      showToast(msg, { variant: "error" });
    } finally {
      setExplainingCellId(null);
    }
  }

  function handleDeleteCell(cellId: string) {
    if (!activeNb) return;
    const removedIndex = activeNb.cells.findIndex((c) => c.id === cellId);
    if (removedIndex === -1) return;

    const removedCell = activeNb.cells[removedIndex];
    const targetNbId = activeNb.id;

    setActiveNb((prev) => {
      if (!prev || prev.id !== targetNbId) return prev;
      return {
        ...prev,
        cells: prev.cells
          .filter((c) => c.id !== cellId)
          .map((c, idx) => ({ ...c, position: idx })),
      };
    });
    setDirty(true);

    showToast(`In [${removedIndex + 1}] removed`, {
      variant: "info",
      durationMs: 5000,
      action: {
        label: "Undo",
        onClick: () => {
          setActiveNb((prev) => {
            if (!prev || prev.id !== targetNbId) return prev;
            if (prev.cells.some((c) => c.id === removedCell.id)) return prev;
            const nextCells = [...prev.cells];
            const insertAt = Math.min(removedIndex, nextCells.length);
            nextCells.splice(insertAt, 0, removedCell);
            return {
              ...prev,
              cells: nextCells.map((c, idx) => ({ ...c, position: idx })),
            };
          });
          setDirty(true);
          showToast("Cell restored", { variant: "success" });
        },
      },
    });
  }

  function reorderCell(fromIndex: number, toIndex: number) {
    if (!activeNb) return;
    if (
      fromIndex === toIndex ||
      fromIndex < 0 ||
      toIndex < 0 ||
      fromIndex >= activeNb.cells.length ||
      toIndex >= activeNb.cells.length
    ) {
      return;
    }
    const nextCells = [...activeNb.cells];
    const [moved] = nextCells.splice(fromIndex, 1);
    nextCells.splice(toIndex, 0, moved);
    setActiveNb({
      ...activeNb,
      cells: nextCells.map((c, idx) => ({ ...c, position: idx })),
    });
    setDirty(true);
  }

  function handleMoveCell(index: number, direction: -1 | 1) {
    reorderCell(index, index + direction);
  }

  function handleOperationChange(cell: NotebookCell, nextOp: string) {
    const isBinaryMatrix = nextOp === "matrix_add" || nextOp === "matrix_multiply";
    const isSingleMatrix =
      nextOp.startsWith("matrix_") && !isBinaryMatrix;

    let nextOptions = { ...(cell.options || {}) };
    if (nextOp === "linear_system_solve") {
      if (!nextOptions.matrix) {
        nextOptions = { matrix: [[2, 1], [1, -1]], vector: [5, 1] };
      } else if (!nextOptions.vector) {
        const rows = normalizeMatrixData(nextOptions.matrix).length;
        nextOptions = { ...nextOptions, vector: normalizeVectorData(undefined, rows) };
      }
    } else if (isBinaryMatrix && (!nextOptions.matrix_a || !nextOptions.matrix_b)) {
      nextOptions = {
        matrix_a: normalizeMatrixData(nextOptions.matrix_a ?? nextOptions.matrix),
        matrix_b: normalizeMatrixData(nextOptions.matrix_b),
      };
    } else if (isSingleMatrix && !nextOptions.matrix) {
      nextOptions = { matrix: normalizeMatrixData(nextOptions.matrix_a) };
    }

    const prevOp = (cell.operation ?? "simplify").trim().toLowerCase();
    const isNextMatrixLike = nextOp.startsWith("matrix_") || nextOp === "linear_system_solve";
    const patch: Partial<NotebookCell> = {
      operation: nextOp,
      options: nextOptions,
      ...(isNextMatrixLike ? { depends_on: [] } : {}),
    };

    // Moving from an expression/assign cell into Solve or Root Find strips a leading
    // `f = expr` label into `Save as` so users don't accidentally create a 2-variable equation.
    if (
      (nextOp === "solve" || nextOp === "root_find") &&
      prevOp !== "solve" &&
      prevOp !== "root_find" &&
      prevOp !== "solve_ode"
    ) {
      const rawExpr = (cell.expression ?? "").trim();
      const eqMatch = /^([a-zA-Z][a-zA-Z0-9_]{0,15})\s*=\s*(.+)$/.exec(rawExpr);
      const activeVar = (cell.variable ?? "").trim();
      if (
        eqMatch &&
        !/^(?:e|i|pi|oo|inf)$/i.test(eqMatch[1]) &&
        eqMatch[1] !== activeVar &&
        !/^0(?:\.0+)?$/.test(eqMatch[2].trim())
      ) {
        patch.expression = eqMatch[2].trim();
        if (!cell.assign_to?.trim()) {
          patch.assign_to = eqMatch[1];
        }
      }
    }

    updateLocalCell(cell.id, patch);
    setOptionsDrafts((prev) => ({
      ...prev,
      [cell.id]: JSON.stringify(nextOptions, null, 2),
    }));
  }

  const handleSave = useCallback(async (silentToast = false): Promise<NotebookResponse | null> => {
    if (!activeNb) return null;
    for (const cell of activeNb.cells) {
      const draft = optionsDrafts[cell.id];
      if (draft !== undefined && draft.trim() !== "") {
        try {
          const parsed: unknown = JSON.parse(draft);
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            const msg = "Cell options must be a valid JSON object.";
            setError(msg);
            showToast(msg, { variant: "error" });
            return null;
          }
        } catch {
          const msg = "One of the cells has malformed JSON in Options.";
          setError(msg);
          showToast(msg, { variant: "error" });
          return null;
        }
      }
    }

    setError(null);
    setBusy(true);
    try {
      const payload = {
        title: activeNb.title,
        mode: activeNb.mode,
        cells: toCellInputs(activeNb.cells),
      };
      const saved = isAuthenticated
        ? await updateNotebook(activeNb.id, payload)
        : updateGuestNotebook(activeNb.id, payload);
      setActiveNb(saved);
      setOptionsDrafts({});
      setDirty(false);
      setJustSaved(true);
      setSummaries(isAuthenticated ? await listNotebooks() : listGuestNotebooks());
      if (!silentToast) {
        showToast("Notebook saved", { detail: saved.title, variant: "success" });
      }
      return saved;
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to save notebook.";
      setError(msg);
      showToast(msg, { variant: "error" });
      return null;
    } finally {
      setBusy(false);
    }
  }, [activeNb, isAuthenticated, optionsDrafts]);

  useEffect(() => {
    if (!justSaved) return;
    const timer = window.setTimeout(() => setJustSaved(false), 2200);
    return () => window.clearTimeout(timer);
  }, [justSaved]);

  useEffect(() => {
    if (!dirty) return;
    function onBeforeUnload(e: BeforeUnloadEvent) {
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (activeNb && dirty && !busy) {
          void handleSave();
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeNb, dirty, busy, handleSave]);

  function reportExecutionToast(executedIds: string[], resultCells: NotebookCell[]) {
    if (executedIds.length === 0) {
      showToast("All cells are up to date", { variant: "info" });
      return;
    }
    const executedSet = new Set(executedIds);
    const failedCount = resultCells.filter(
      (c) => executedSet.has(c.id) && c.status === "error"
    ).length;
    if (failedCount > 0) {
      showToast("Execution finished with errors", {
        detail: `${failedCount} cell${failedCount > 1 ? "s" : ""} failed`,
        variant: "error",
      });
      return;
    }
    showToast("Executed successfully", {
      detail: `${executedIds.length} cell${executedIds.length > 1 ? "s" : ""} ran`,
      variant: "success",
    });
  }

  async function handleExecute(onlyStale = false, upToCellId?: string) {
    if (!activeNb) return;
    setError(null);
    let targetNb = activeNb;
    if (dirty) {
      const saved = await handleSave(true);
      if (!saved) return;
      targetNb = saved;
    }

    setBusy(true);
    try {
      if (!isAuthenticated) {
        const res = await executeStatelessNotebook({
          id: targetNb.id,
          title: targetNb.title,
          mode: targetNb.mode,
          created_at: targetNb.created_at,
          cells: targetNb.cells,
          variables: targetNb.variables,
          only_stale: onlyStale,
          up_to_cell_id: upToCellId ?? null,
        });
        const persistedLocally = saveGuestNotebookSnapshot(res.notebook);
        setActiveNb(persistedLocally);
        setDirty(false);
        setSummaries(listGuestNotebooks());
        reportExecutionToast(res.executed_cell_ids, persistedLocally.cells);
        return;
      }

      const res = await executeNotebook(targetNb.id, {
        only_stale: onlyStale,
        up_to_cell_id: upToCellId ?? null,
      });
      setActiveNb(res.notebook);
      setDirty(false);
      setSummaries(await listNotebooks());
      reportExecutionToast(res.executed_cell_ids, res.notebook.cells);
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Notebook execution failed.";
      setError(msg);
      showToast(msg, { variant: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleMode(nextMode: NotebookMode) {
    if (!activeNb || activeNb.mode === nextMode) return;
    setActiveNb({ ...activeNb, mode: nextMode });
    try {
      const saved = isAuthenticated
        ? await updateNotebook(activeNb.id, { mode: nextMode })
        : updateGuestNotebook(activeNb.id, { mode: nextMode });
      setActiveNb(saved);
    } catch {
      setDirty(true);
    }
  }

  const opNames = [
    "assign",
    ...(operations.length > 0
      ? operations.map((o) => o.name)
      : [
          "simplify",
          "expand",
          "factor",
          "solve",
          "differentiate",
          "integrate",
          "limit",
          "partial_derivative",
          "taylor_series",
          "solve_ode",
          "linear_system_solve",
          "numerical_eval",
          "root_find",
        ]),
  ];

  return (
    <div className="grid gap-8 lg:grid-cols-[268px_1fr]">
      {/* Left Sidebar */}
      <aside className="space-y-6 lg:border-r lg:border-[var(--border-hairline)] lg:pr-6">
        <div>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Notebooks
              </h2>
              <p className="font-mono text-[11px] text-[var(--text-muted)]">
                {isAuthenticated ? "Cloud synced" : "Guest · Local browser storage"}
              </p>
            </div>
            <button
              type="button"
              onClick={() => void handleCreateNotebook()}
              disabled={busy}
              className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
            >
              + New
            </button>
          </div>

          {isAuthenticated && guestPendingCount > 0 && (
            <div className="mb-3 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-2.5 text-[11px]">
              <p className="text-[var(--text-secondary)]">
                {guestPendingCount} local guest notebook{guestPendingCount > 1 ? "s" : ""} found in
                this browser.
              </p>
              <button
                type="button"
                onClick={() => void handleImportGuestNotebooks()}
                disabled={busy}
                className="mt-1.5 rounded bg-[var(--accent-ink)] px-2.5 py-1 text-[11px] font-medium text-[var(--accent-ink-fg)] hover:opacity-90 disabled:opacity-50"
              >
                Import to Cloud
              </button>
            </div>
          )}

          {loadingList ? (
            <p className="font-mono text-xs text-[var(--text-muted)]">Loading notebooks...</p>
          ) : summaries.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)]">
              No notebooks yet. Click + New to create one.
            </p>
          ) : (
            <ul className="max-h-40 space-y-0.5 overflow-y-auto lg:max-h-none">
              {summaries.map((item) => {
                const selected = activeNb?.id === item.id;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => void handleSelectNotebook(item.id)}
                      className={`w-full rounded px-2.5 py-1.5 text-left text-xs transition ${
                        selected
                          ? "bg-[var(--bg-subtle)] font-medium text-[var(--text-primary)]"
                          : "text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]/60 hover:text-[var(--text-primary)]"
                      }`}
                    >
                      <div className="truncate">{item.title}</div>
                      <div className="text-[10px] text-[var(--text-muted)]">
                        {item.cell_count} cells · {item.mode}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {activeNb && (
          <div className="border-t border-[var(--border-hairline)] pt-4">
            <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Active Symbols
            </h2>
            {Object.keys(activeNb.variables).length === 0 ? (
              <p className="text-xs text-[var(--text-muted)]">
                Bind symbols via <code>assign</code> or <code>assign_to</code>.
              </p>
            ) : (
              <div className="space-y-1.5">
                {Object.values(activeNb.variables).map((v) => (
                  <div
                    key={v.symbol_name}
                    className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-xs"
                  >
                    <div className="font-mono text-[11px] font-semibold text-[var(--text-primary)]">
                      {v.symbol_name}
                    </div>
                    <LatexBlock latex={v.value_latex} displayMode={false} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </aside>

      {/* Main Document Canvas */}
      <section className="min-w-0 space-y-5">
        {error && (
          <div className="rounded border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-600">
            {error}
          </div>
        )}

        {!activeNb ? (
          loadingList ? (
            <div className="rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-10 text-center">
              <p className="font-mono text-xs text-[var(--text-muted)]">
                Loading notebooks...
              </p>
            </div>
          ) : (
          <div className="rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-10 text-center">
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              No Notebook Selected
            </h2>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              {isAuthenticated
                ? "Create a notebook to evaluate expressions sequentially, track dependencies, and sync results to your cloud account."
                : "Guest Mode saves notebooks locally in this browser. Sign in anytime to sync notebooks to the cloud."}
            </p>
            <button
              type="button"
              onClick={() => void handleCreateNotebook()}
              className="mt-4 rounded bg-[var(--accent-ink)] px-4 py-2 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90"
            >
              Create First Notebook
            </button>
          </div>
          )
        ) : (
          <>
            {/* Notebook Header */}
            <div className="space-y-2.5 border-b border-[var(--border-hairline)] pb-3.5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-[200px] flex-1 items-center gap-2">
                  <input
                    type="text"
                    value={activeNb.title}
                    onChange={(e) => {
                      setActiveNb({ ...activeNb, title: e.target.value });
                      setDirty(true);
                    }}
                    className="w-full rounded border border-transparent bg-transparent px-1.5 py-0.5 text-lg font-semibold tracking-tight text-[var(--text-primary)] hover:border-[var(--border-hairline)] focus:border-[var(--border-strong)] focus:bg-[var(--bg-surface)] focus:outline-none"
                  />
                  {dirty ? (
                    <span className="shrink-0 font-mono text-[11px] text-[var(--status-warn)]">
                      • unsaved
                    </span>
                  ) : justSaved ? (
                    <span className="shrink-0 font-mono text-[11px] text-[var(--status-verified)]">
                      ✓ saved
                    </span>
                  ) : null}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="inline-flex rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-0.5 text-xs">
                    {(["computational", "learning"] as const).map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => void handleToggleMode(m)}
                        className={`rounded-sm px-2.5 py-1 capitalize ${
                          activeNb.mode === m
                            ? "bg-[var(--bg-surface)] font-medium text-[var(--text-primary)] shadow-xs"
                            : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>

                  <button
                    type="button"
                    onClick={() => void handleSave()}
                    disabled={busy || !dirty}
                    className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] disabled:opacity-40"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleExecute(true)}
                    disabled={busy}
                    title="Re-run only outdated, ready (unrun), or errored cells and skip valid cells"
                    className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] disabled:opacity-50"
                  >
                    Run Outdated
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleExecute(false)}
                    disabled={busy}
                    title="Re-run every math cell in order from a clean variable state"
                    className="rounded bg-[var(--accent-ink)] px-3 py-1 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90 disabled:opacity-60"
                  >
                    {busy ? "Running..." : "Run All"}
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-end gap-2 text-xs">
                {isAuthenticated && (
                  <button
                    type="button"
                    onClick={() => void handleOpenHistory()}
                    disabled={busy}
                    className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  >
                    History
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => void handleExport("markdown")}
                  className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  Export .md
                </button>
                <button
                  type="button"
                  onClick={() => void handleExport("json")}
                  className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  Export .json
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDeleteOpen(true)}
                  disabled={busy}
                  className="ml-1 rounded border border-rose-500/25 bg-[var(--bg-surface)] px-2.5 py-1 text-rose-500/80 transition hover:border-rose-500/50 hover:bg-rose-500/10 hover:text-rose-500"
                >
                  Delete Notebook
                </button>
              </div>
            </div>

            {activeNb.mode === "learning" && (
              <LearningAssistantPanel
                mode={activeNb.mode}
                examples={examples}
                onInsertCell={(cell) => handleAddCell(cell)}
              />
            )}

            {/* Document Cells with Responsive Gutter */}
            <div className="divide-y divide-[var(--border-hairline)] rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)]">
              {activeNb.cells.map((cell, index) => {
                const dragStateClass = `${dragSourceIdx === index ? "opacity-50" : ""} ${
                  dragOverIdx === index && dragSourceIdx !== index
                    ? "ring-1 ring-inset ring-[var(--text-primary)] bg-[var(--bg-subtle)]/50"
                    : ""
                }`;

                const cellDropHandlers = {
                  onDragOver: (e: DragEvent<HTMLDivElement>) => {
                    if (dragSourceIdx !== null) {
                      e.preventDefault();
                      if (dragOverIdx !== index) setDragOverIdx(index);
                    }
                  },
                  onDrop: (e: DragEvent<HTMLDivElement>) => {
                    e.preventDefault();
                    if (dragSourceIdx !== null && dragSourceIdx !== index) {
                      reorderCell(dragSourceIdx, index);
                    }
                    setDragSourceIdx(null);
                    setDragOverIdx(null);
                  },
                };

                const gripDragHandlers = {
                  draggable: true,
                  onDragStart: (e: DragEvent<HTMLDivElement>) => {
                    setDragSourceIdx(index);
                    e.dataTransfer.effectAllowed = "move";
                    e.dataTransfer.setData("text/plain", cell.id);
                  },
                  onDragEnd: () => {
                    setDragSourceIdx(null);
                    setDragOverIdx(null);
                  },
                };

                if (cell.cell_type === "markdown") {
                  const isEditingMd = editingMarkdownIds[cell.id] ?? false;
                  return (
                    <div
                      key={cell.id}
                      {...cellDropHandlers}
                      className={`flex flex-col gap-2.5 bg-[var(--bg-subtle)]/30 p-3 transition sm:grid sm:grid-cols-[64px_1fr] sm:gap-3 sm:p-4 ${dragStateClass}`}
                    >
                      <div
                        {...gripDragHandlers}
                        title="Drag to reorder cell"
                        className="flex cursor-grab select-none flex-row items-center justify-between font-mono text-[11px] text-[var(--text-muted)] active:cursor-grabbing sm:flex-col sm:items-end sm:justify-start sm:pt-1"
                      >
                        <span className="inline-flex items-center gap-1 hover:text-[var(--text-primary)]">
                          <span className="tracking-tighter opacity-60">⋮⋮</span>
                          <span>Note [{index + 1}]</span>
                        </span>
                        <span className="text-[10px] sm:mt-1">markdown</span>
                      </div>

                      <div className="min-w-0 space-y-2">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                            Markdown Note
                          </span>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => handleMoveCell(index, -1)}
                              disabled={index === 0}
                              title="Move cell up"
                              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] disabled:opacity-30"
                            >
                              ↑
                            </button>
                            <button
                              type="button"
                              onClick={() => handleMoveCell(index, 1)}
                              disabled={index === activeNb.cells.length - 1}
                              title="Move cell down"
                              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] disabled:opacity-30"
                            >
                              ↓
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                setEditingMarkdownIds((prev) => ({
                                  ...prev,
                                  [cell.id]: !isEditingMd,
                                }))
                              }
                              className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                            >
                              {isEditingMd ? "Preview" : "Edit"}
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteCell(cell.id)}
                              className="text-[var(--text-muted)] hover:text-[var(--status-error)]"
                              title="Remove note cell"
                            >
                              Remove
                            </button>
                          </div>
                        </div>

                        {isEditingMd ? (
                          <textarea
                            rows={3}
                            value={cell.expression ?? ""}
                            onChange={(e) =>
                              updateLocalCell(cell.id, { expression: e.target.value })
                            }
                            placeholder="Write notes, headings (# Title), or derivation commentary..."
                            className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
                          />
                        ) : (
                          <div className="space-y-1 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-2.5">
                            {renderMarkdownLines(cell.expression ?? "")}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                }

                const op = cell.operation ?? "simplify";
                const isMatrixLike = op.startsWith("matrix_") || op === "linear_system_solve";
                const nonMatrixOptionKeys = Object.keys(cell.options || {}).filter(
                  (k) => k !== "matrix" && k !== "matrix_a" && k !== "matrix_b" && k !== "vector"
                );
                const showOptions =
                  Boolean(openOptionsCellIds[cell.id]) ||
                  nonMatrixOptionKeys.length > 0 ||
                  Object.keys(cell.assumptions || {}).length > 0;

                return (
                  <div
                    key={cell.id}
                    {...cellDropHandlers}
                    className={`flex flex-col gap-2.5 p-3 transition sm:grid sm:grid-cols-[64px_1fr] sm:gap-3 sm:p-4 ${dragStateClass}`}
                  >
                    <div
                      {...gripDragHandlers}
                      title="Drag to reorder cell"
                      className="flex cursor-grab select-none flex-row items-center justify-between font-mono text-[11px] text-[var(--text-muted)] active:cursor-grabbing sm:flex-col sm:items-end sm:justify-start sm:pt-1"
                    >
                      <span className="inline-flex items-center gap-1 hover:text-[var(--text-primary)]">
                        <span className="tracking-tighter opacity-60">⋮⋮</span>
                        <span>In [{index + 1}]</span>
                      </span>
                      <span
                        className="flex items-center gap-1 text-[10px] sm:mt-1.5"
                        title={
                          cell.status === "stale"
                            ? "Input or an upstream variable changed — click Run to update"
                            : `Status: ${STATUS_LABEL[cell.status]}`
                        }
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[cell.status]}`} />
                        {STATUS_LABEL[cell.status]}
                      </span>
                    </div>

                    <div className="min-w-0 space-y-2.5">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                        <div className="flex flex-wrap items-center gap-2">
                          <select
                            value={op}
                            onChange={(e) => handleOperationChange(cell, e.target.value)}
                            aria-label="Cell operation"
                            className="rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-2.5 py-1 text-xs font-medium text-[var(--text-primary)] focus:border-[var(--text-primary)] focus:outline-none"
                          >
                            {opNames.map((name) => (
                              <option key={name} value={name}>
                                {formatOperationLabel(name)}
                              </option>
                            ))}
                          </select>

                          {OPS_WITH_VARIABLE.has(op) && (
                            <label
                              className="inline-flex items-center overflow-hidden rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px]"
                              title="Target variable (leave blank for auto-detection)"
                            >
                              <span className="border-r border-[var(--border-hairline)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-muted)]">
                                {OP_VAR_LABELS[op] ?? "Variable"}
                              </span>
                              <input
                                type="text"
                                value={cell.variable ?? ""}
                                onChange={(e) =>
                                  updateLocalCell(cell.id, { variable: e.target.value || null })
                                }
                                placeholder="auto"
                                className="w-14 bg-[var(--bg-surface)] px-2 py-0.5 font-mono text-[11px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]/70 focus:outline-none"
                              />
                            </label>
                          )}

                          {op === "limit" && (
                            <label
                              className="inline-flex items-center overflow-hidden rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px]"
                              title="Limit target point (e.g. 0, 1, oo)"
                            >
                              <span className="border-r border-[var(--border-hairline)] px-2 py-0.5 font-mono text-[10px] font-medium text-[var(--text-muted)]">
                                →
                              </span>
                              <input
                                type="text"
                                value={String(cell.options?.point ?? "")}
                                onChange={(e) =>
                                  updateCellOptionField(cell, "point", e.target.value)
                                }
                                placeholder="0"
                                className="w-14 bg-[var(--bg-surface)] px-2 py-0.5 font-mono text-[11px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]/70 focus:outline-none"
                              />
                            </label>
                          )}

                          {(op === "integrate" || op === "numerical_integrate") && (
                            <div
                              className="inline-flex items-center overflow-hidden rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px]"
                              title="Optional definite integral bounds [from, to]"
                            >
                              <span className="border-r border-[var(--border-hairline)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-muted)]">
                                ∫ from
                              </span>
                              <input
                                type="text"
                                value={String(cell.options?.lower ?? "")}
                                onChange={(e) =>
                                  updateCellOptionField(cell, "lower", e.target.value)
                                }
                                placeholder="a"
                                className="w-11 bg-[var(--bg-surface)] px-1.5 py-0.5 text-center font-mono text-[11px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]/70 focus:outline-none"
                              />
                              <span className="border-x border-[var(--border-hairline)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-muted)]">
                                to
                              </span>
                              <input
                                type="text"
                                value={String(cell.options?.upper ?? "")}
                                onChange={(e) =>
                                  updateCellOptionField(cell, "upper", e.target.value)
                                }
                                placeholder="b"
                                className="w-11 bg-[var(--bg-surface)] px-1.5 py-0.5 text-center font-mono text-[11px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]/70 focus:outline-none"
                              />
                            </div>
                          )}

                          {op === "taylor_series" && (
                            <div className="inline-flex items-center overflow-hidden rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px]">
                              <span className="border-r border-[var(--border-hairline)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-muted)]">
                                at
                              </span>
                              <input
                                type="text"
                                value={String(cell.options?.point ?? "")}
                                onChange={(e) =>
                                  updateCellOptionField(cell, "point", e.target.value)
                                }
                                placeholder="0"
                                className="w-12 bg-[var(--bg-surface)] px-1.5 py-0.5 text-center font-mono text-[11px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]/70 focus:outline-none"
                              />
                              <span className="border-x border-[var(--border-hairline)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-muted)]">
                                order
                              </span>
                              <input
                                type="number"
                                min={1}
                                max={12}
                                value={Number(cell.options?.order ?? 5)}
                                onChange={(e) =>
                                  updateCellOptionField(cell, "order", Number(e.target.value))
                                }
                                className="w-12 bg-[var(--bg-surface)] px-1.5 py-0.5 text-center font-mono text-[11px] text-[var(--text-primary)] focus:outline-none"
                              />
                            </div>
                          )}

                          {op !== "assign" && (
                            <label
                              className="inline-flex items-center overflow-hidden rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px]"
                              title="Optional symbol name to store this result for downstream cells"
                            >
                              <span className="border-r border-[var(--border-hairline)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-muted)]">
                                Save as
                              </span>
                              <input
                                type="text"
                                value={cell.assign_to ?? ""}
                                onChange={(e) =>
                                  updateLocalCell(cell.id, { assign_to: e.target.value || null })
                                }
                                placeholder="optional"
                                className="w-16 bg-[var(--bg-surface)] px-2 py-0.5 font-mono text-[11px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]/70 focus:outline-none"
                              />
                            </label>
                          )}

                          {cell.depends_on.length > 0 && (
                            <span className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-muted)]">
                              deps: {cell.depends_on.length}
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5 text-xs">
                          <div className="inline-flex overflow-hidden rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)]">
                            <button
                              type="button"
                              onClick={() => handleMoveCell(index, -1)}
                              disabled={index === 0}
                              title="Move cell up"
                              className="px-2 py-1 text-[var(--text-secondary)] transition hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)] disabled:opacity-30"
                            >
                              ↑
                            </button>
                            <button
                              type="button"
                              onClick={() => handleMoveCell(index, 1)}
                              disabled={index === activeNb.cells.length - 1}
                              title="Move cell down"
                              className="border-l border-[var(--border-hairline)] px-2 py-1 text-[var(--text-secondary)] transition hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)] disabled:opacity-30"
                            >
                              ↓
                            </button>
                          </div>
                          {!isMatrixLike && (
                            <button
                              type="button"
                              onClick={() =>
                                setKeypadCellId((prev) => (prev === cell.id ? null : cell.id))
                              }
                              className={
                                keypadCellId === cell.id
                                  ? CELL_ACTION_ACTIVE_BTN
                                  : CELL_ACTION_BTN
                              }
                            >
                              {keypadCellId === cell.id ? "Hide Keypad" : "Keypad"}
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => toggleOptionsPanel(cell)}
                            className={showOptions ? CELL_ACTION_ACTIVE_BTN : CELL_ACTION_BTN}
                          >
                            {showOptions ? "Hide Options" : "Options"}
                          </button>
                          {op !== "assign" && (
                            <button
                              type="button"
                              onClick={() => void handleExplainCell(cell)}
                              disabled={explainingCellId === cell.id}
                              className={
                                cellExplanations[cell.id]
                                  ? CELL_ACTION_ACTIVE_BTN
                                  : CELL_ACTION_BTN
                              }
                            >
                              {explainingCellId === cell.id
                                ? "Explaining..."
                                : cellExplanations[cell.id]
                                  ? "Hide Guide"
                                  : "Explain"}
                            </button>
                          )}
                          {isMatrixLike
                            ? (() => {
                                const matrixSeed = buildMatrixPlotSeed(
                                  op,
                                  cell.options,
                                  cell.result?.metadata?.details as
                                    | Record<string, unknown>
                                    | undefined
                                );
                                if (!matrixSeed) return null;
                                return (
                                  <button
                                    type="button"
                                    onClick={() => onPlotExpression(matrixSeed)}
                                    title="Visualize matrix transformation, linear system, or heatmap"
                                    className={CELL_ACTION_BTN}
                                  >
                                    {matrixSeed.matrixB && cell.result ? "Plot Result" : "Plot"}
                                  </button>
                                );
                              })()
                            : cell.expression &&
                              op !== "assign" &&
                              (() => {
                                const raw = (cell.expression ?? "").trim();
                                const stripped = stripInlineAssignForOp(raw, op);
                                const lookedUp = activeNb.variables[stripped]?.value_expr ?? raw;
                                const plotExpr = preparePlottableExpression(lookedUp, op);
                                const compareResult = extractPlottableCompareResult(
                                  cell.result?.result_text,
                                  plotExpr
                                );
                                return (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      onPlotExpression({
                                        plotType: "2d",
                                        expr: plotExpr,
                                        compareExpr: compareResult,
                                        variable: cell.variable ?? undefined,
                                      })
                                    }
                                    title={
                                      compareResult
                                        ? "Plot input and computed result in Visualization Studio"
                                        : "Plot expression in Visualization Studio"
                                    }
                                    className={CELL_ACTION_BTN}
                                  >
                                    {compareResult ? "Plot Result" : "Plot"}
                                  </button>
                                );
                              })()}
                          <button
                            type="button"
                            onClick={() => void handleExecute(false, cell.id)}
                            disabled={busy}
                            title="Run up to this cell (Shift + Enter)"
                            className="rounded bg-[var(--accent-ink)] px-3 py-1 font-semibold text-[var(--accent-ink-fg)] transition hover:opacity-90 disabled:opacity-50"
                          >
                            Run
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteCell(cell.id)}
                            className="rounded border border-rose-500/25 bg-[var(--bg-subtle)] px-2.5 py-1 text-rose-500/80 transition hover:border-rose-500/50 hover:bg-rose-500/10 hover:text-rose-500"
                            title="Remove cell"
                          >
                            Remove
                          </button>
                        </div>
                      </div>

                      {!isMatrixLike ? (
                        <div className="space-y-1.5">
                          <CodeMirrorCellEditor
                            ref={(handle) => {
                              editorRefs.current[cell.id] = handle;
                            }}
                            value={cell.expression ?? ""}
                            onChange={(next) => updateLocalCell(cell.id, { expression: next })}
                            onRunCell={() => void handleExecute(false, cell.id)}
                            placeholder={
                              OP_PLACEHOLDERS[op] ??
                              "Enter expression (Shift+Enter to run)"
                            }
                          />

                          {keypadCellId === cell.id && (
                            <MathKeypad
                              onInsert={(text, cursorBack) =>
                                editorRefs.current[cell.id]?.insertText(text, cursorBack)
                              }
                              onBackspace={() => editorRefs.current[cell.id]?.backspace()}
                              onClear={() => editorRefs.current[cell.id]?.clear()}
                              onRun={() => void handleExecute(false, cell.id)}
                              onClose={() => setKeypadCellId(null)}
                            />
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-wrap items-start gap-3">
                          {op === "matrix_add" || op === "matrix_multiply" ? (
                            <>
                              <MatrixGridEditor
                                label="Matrix A"
                                value={cell.options?.matrix_a ?? cell.options?.matrix}
                                onChange={(nextMatrix: MatrixData) =>
                                  updateCellOptionField(cell, "matrix_a", nextMatrix)
                                }
                              />
                              <MatrixGridEditor
                                label="Matrix B"
                                value={cell.options?.matrix_b}
                                onChange={(nextMatrix: MatrixData) =>
                                  updateCellOptionField(cell, "matrix_b", nextMatrix)
                                }
                              />
                            </>
                          ) : op === "linear_system_solve" ? (
                            <>
                              <MatrixGridEditor
                                label="Matrix A"
                                value={cell.options?.matrix}
                                onChange={(nextMatrix: MatrixData) => {
                                  const nextOpts = {
                                    ...(cell.options || {}),
                                    matrix: nextMatrix,
                                    vector: normalizeVectorData(
                                      cell.options?.vector,
                                      nextMatrix.length
                                    ),
                                  };
                                  updateLocalCell(cell.id, { options: nextOpts });
                                  setOptionsDrafts((prev) => ({
                                    ...prev,
                                    [cell.id]: JSON.stringify(nextOpts, null, 2),
                                  }));
                                }}
                              />
                              <VectorGridEditor
                                label="Vector b"
                                length={normalizeMatrixData(cell.options?.matrix).length}
                                value={cell.options?.vector}
                                onChange={(nextVec) =>
                                  updateCellOptionField(cell, "vector", nextVec)
                                }
                              />
                            </>
                          ) : (
                            <MatrixGridEditor
                              label="Matrix"
                              value={cell.options?.matrix}
                              onChange={(nextMatrix: MatrixData) =>
                                updateCellOptionField(cell, "matrix", nextMatrix)
                              }
                            />
                          )}
                        </div>
                      )}

                      {(() => {
                        const notationLatex = formatCellNotationLatex({
                          operation: op,
                          expression: cell.expression,
                          variable: cell.variable,
                          assignTo: cell.assign_to,
                          options: cell.options,
                        });
                        if (!notationLatex) return null;
                        return (
                          <div className="flex items-center gap-2.5 overflow-x-auto overflow-y-hidden rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)]/50 px-3 py-1 text-xs">
                            <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                              Notation
                            </span>
                            <LatexBlock latex={notationLatex} displayMode={false} />
                          </div>
                        );
                      })()}

                      {showOptions && (
                        <div className="space-y-2 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-2.5 text-[11px]">
                          {(op === "integrate" || op === "numerical_integrate") && (
                            <div className="flex flex-wrap gap-3">
                              <label className="flex items-center gap-1.5 font-mono text-[var(--text-secondary)]">
                                lower:
                                <input
                                  type="text"
                                  value={String(cell.options?.lower ?? "")}
                                  onChange={(e) =>
                                    updateCellOptionField(cell, "lower", e.target.value)
                                  }
                                  placeholder="e.g. 0"
                                  className="w-20 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 text-[var(--text-primary)]"
                                />
                              </label>
                              <label className="flex items-center gap-1.5 font-mono text-[var(--text-secondary)]">
                                upper:
                                <input
                                  type="text"
                                  value={String(cell.options?.upper ?? "")}
                                  onChange={(e) =>
                                    updateCellOptionField(cell, "upper", e.target.value)
                                  }
                                  placeholder="e.g. 3"
                                  className="w-20 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 text-[var(--text-primary)]"
                                />
                              </label>
                            </div>
                          )}

                          {(op === "limit" || op === "taylor_series") && (
                            <div className="flex flex-wrap gap-3">
                              <label className="flex items-center gap-1.5 font-mono text-[var(--text-secondary)]">
                                point:
                                <input
                                  type="text"
                                  value={String(cell.options?.point ?? "")}
                                  onChange={(e) =>
                                    updateCellOptionField(cell, "point", e.target.value)
                                  }
                                  placeholder="0"
                                  className="w-20 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 text-[var(--text-primary)]"
                                />
                              </label>
                              {op === "taylor_series" && (
                                <label className="flex items-center gap-1.5 font-mono text-[var(--text-secondary)]">
                                  order:
                                  <input
                                    type="number"
                                    min={1}
                                    max={12}
                                    value={Number(cell.options?.order ?? 5)}
                                    onChange={(e) =>
                                      updateCellOptionField(cell, "order", Number(e.target.value))
                                    }
                                    className="w-16 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 text-[var(--text-primary)]"
                                  />
                                </label>
                              )}
                            </div>
                          )}

                          {op === "root_find" && (
                            <div className="flex flex-wrap gap-3">
                              <label className="flex items-center gap-1.5 font-mono text-[var(--text-secondary)]">
                                min:
                                <input
                                  type="number"
                                  step="any"
                                  value={
                                    Array.isArray(cell.options?.bracket)
                                      ? String(cell.options.bracket[0] ?? 0)
                                      : ""
                                  }
                                  onChange={(e) => {
                                    const cur = Array.isArray(cell.options?.bracket)
                                      ? cell.options.bracket
                                      : [0, 2];
                                    updateCellOptionField(cell, "bracket", [
                                      Number(e.target.value),
                                      Number(cur[1] ?? 2),
                                    ]);
                                  }}
                                  placeholder="0"
                                  className="w-20 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 text-[var(--text-primary)]"
                                />
                              </label>
                              <label className="flex items-center gap-1.5 font-mono text-[var(--text-secondary)]">
                                max:
                                <input
                                  type="number"
                                  step="any"
                                  value={
                                    Array.isArray(cell.options?.bracket)
                                      ? String(cell.options.bracket[1] ?? 2)
                                      : ""
                                  }
                                  onChange={(e) => {
                                    const cur = Array.isArray(cell.options?.bracket)
                                      ? cell.options.bracket
                                      : [0, 2];
                                    updateCellOptionField(cell, "bracket", [
                                      Number(cur[0] ?? 0),
                                      Number(e.target.value),
                                    ]);
                                  }}
                                  placeholder="2"
                                  className="w-20 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 text-[var(--text-primary)]"
                                />
                              </label>
                            </div>
                          )}

                          <AssumptionsEditor
                            compact
                            assumptions={cell.assumptions || {}}
                            onChange={(next) => updateLocalCell(cell.id, { assumptions: next })}
                          />

                          <details className="pt-1">
                            <summary className="cursor-pointer select-none font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)] hover:text-[var(--text-primary)]">
                              Advanced Options (JSON)
                            </summary>
                            <textarea
                              rows={3}
                              value={
                                optionsDrafts[cell.id] ?? JSON.stringify(cell.options || {}, null, 2)
                              }
                              onChange={(e) => handleOptionsJsonChange(cell.id, e.target.value)}
                              className="mt-1.5 w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 py-1 font-mono text-[11px] text-[var(--text-primary)] focus:outline-none"
                            />
                          </details>
                        </div>
                      )}

                      {cell.error_message && (
                        <div className="rounded border border-rose-500/40 bg-rose-500/10 p-2 text-xs text-rose-600">
                          {cell.error_message}
                        </div>
                      )}

                      {cell.result && (
                        <ExplainableOutputPanel
                          resultText={cell.result.result_text}
                          resultLatex={cell.result.result_latex}
                          reasoning={cell.result.reasoning}
                          verification={cell.result.verification}
                          learningMode={activeNb.mode === "learning"}
                        />
                      )}

                      {cellExplanations[cell.id] && (
                        <StepByStepGuide
                          sourceLabel={
                            cellExplanations[cell.id].explanation_source === "llm_grounded"
                              ? "AI Grounded"
                              : "Step Walkthrough"
                          }
                          summary={cellExplanations[cell.id].summary}
                          steps={cellExplanations[cell.id].steps}
                          onClose={() => void handleExplainCell(cell)}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => handleAddCell()}
                className="w-full rounded border border-dashed border-[var(--border-strong)] py-2 text-xs font-medium text-[var(--text-secondary)] transition hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"
              >
                + Add Math Cell
              </button>
              <button
                type="button"
                onClick={() => handleAddMarkdownCell()}
                className="w-full rounded border border-dashed border-[var(--border-hairline)] py-2 text-xs font-medium text-[var(--text-muted)] transition hover:border-[var(--border-strong)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"
              >
                + Add Markdown Note
              </button>
            </div>
          </>
        )}
      </section>

      <Modal
        open={historyOpen && Boolean(activeNb)}
        onClose={() => setHistoryOpen(false)}
        maxWidthClass="max-w-md"
      >
        {activeNb && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Execution History · {activeNb.title}
              </h2>
              <button
                type="button"
                onClick={() => setHistoryOpen(false)}
                className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              >
                Close
              </button>
            </div>

            <div className="mt-3 max-h-72 space-y-2 overflow-y-auto">
              {historyLoading ? (
                <p className="py-6 text-center font-mono text-xs text-[var(--text-muted)]">
                  Loading snapshots...
                </p>
              ) : historyEntries.length === 0 ? (
                <p className="py-6 text-center text-xs text-[var(--text-muted)]">
                  No execution snapshots recorded yet. Click Run All to record one.
                </p>
              ) : (
                historyEntries.map((entry) => (
                  <div
                    key={entry.id}
                    className="flex items-center justify-between gap-3 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-2.5 text-xs"
                  >
                    <div className="min-w-0">
                      <div className="font-mono text-[11px] text-[var(--text-primary)]">
                        {new Date(entry.created_at).toLocaleString()}
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)]">
                        {entry.executed_cell_ids.length} executed · {entry.skipped_cell_ids.length}{" "}
                        skipped
                      </div>
                    </div>
                    {entry.notebook && (
                      <button
                        type="button"
                        onClick={() => handleRestoreHistory(entry)}
                        className="shrink-0 rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-2.5 py-1 text-[11px] font-medium text-[var(--text-primary)] hover:bg-[var(--bg-canvas)]"
                      >
                        Restore
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </Modal>

      <Modal
        open={confirmDeleteOpen && Boolean(activeNb)}
        onClose={() => {
          if (!busy) setConfirmDeleteOpen(false);
        }}
        maxWidthClass="max-w-xs"
      >
        {activeNb && (
          <>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Delete Notebook?
            </h2>
            <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
              Are you sure you want to delete{" "}
              <span className="font-medium text-[var(--text-primary)]">
                &ldquo;{activeNb.title}&rdquo;
              </span>
              ? This action cannot be undone and removes it from{" "}
              {isAuthenticated ? "your cloud account" : "this browser's local storage"}.
            </p>

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmDeleteOpen(false)}
                disabled={busy}
                className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleDeleteActiveNotebook()}
                disabled={busy}
                className="rounded bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-60"
              >
                {busy ? "Deleting..." : "Delete"}
              </button>
            </div>
          </>
        )}
      </Modal>

      <Modal
        open={Boolean(pendingLeaveAction) && Boolean(activeNb)}
        onClose={() => {
          if (!busy) setPendingLeaveAction(null);
        }}
        maxWidthClass="max-w-sm"
      >
        {activeNb && pendingLeaveAction && (
          <>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Unsaved Changes
            </h2>
            <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
              <span className="font-medium text-[var(--text-primary)]">
                &ldquo;{activeNb.title}&rdquo;
              </span>{" "}
              has unsaved edits. Do you want to save before{" "}
              {pendingLeaveAction.type === "create"
                ? "creating a new notebook"
                : "switching notebooks"}
              ?
            </p>

            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={() => setPendingLeaveAction(null)}
                disabled={busy}
                className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  const action = pendingLeaveAction;
                  setPendingLeaveAction(null);
                  void runPendingLeaveAction(action);
                }}
                disabled={busy}
                className="rounded border border-rose-500/30 bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-rose-500 hover:bg-rose-500/10 disabled:opacity-60"
              >
                Discard
              </button>
              <button
                type="button"
                onClick={() => {
                  const action = pendingLeaveAction;
                  void (async () => {
                    const saved = await handleSave();
                    if (saved) {
                      setPendingLeaveAction(null);
                      await runPendingLeaveAction(action);
                    }
                  })();
                }}
                disabled={busy}
                className="rounded bg-[var(--accent-ink)] px-3 py-1.5 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90 disabled:opacity-60"
              >
                {busy ? "Saving..." : "Save & Continue"}
              </button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
