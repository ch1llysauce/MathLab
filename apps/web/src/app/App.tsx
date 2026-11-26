import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";

import { MathLabLogo } from "../components/common/MathLabLogo";
import { ToastContainer } from "../components/common/Toast";
import {
  type IncomingNotebookCellSeed,
  NotebookWorkbench,
} from "../components/notebook/NotebookWorkbench";
import { AuthPanel } from "../features/authentication/AuthPanel";
import { API_BASE_URL, fetchHealth, fetchOperations } from "../services/api";
import { supabase } from "../services/supabase";
import type {
  HealthResponse,
  NotebookSummary,
  OperationInfo,
  PlotSeed,
} from "../types/compute";

const ComputeTester = lazy(() =>
  import("../components/computation/ComputeTester").then((m) => ({
    default: m.ComputeTester,
  }))
);

const VisualizationStudio = lazy(() =>
  import("../components/visualization/VisualizationStudio").then((m) => ({
    default: m.VisualizationStudio,
  }))
);

type WorkbenchTab = "notebook" | "compute" | "visualize";
type WorkbenchTheme = "light" | "dark";

export function App() {
  const [activeTab, setActiveTab] = useState<WorkbenchTab>("notebook");
  const [theme, setTheme] = useState<WorkbenchTheme>(() => {
    const saved = window.localStorage.getItem("mathlab_theme");
    return saved === "dark" ? "dark" : "light";
  });
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [operations, setOperations] = useState<OperationInfo[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [authVersion, setAuthVersion] = useState(0);
  const [recoveryOpen, setRecoveryOpen] = useState(false);
  const [plotSeed, setPlotSeed] = useState<PlotSeed | undefined>(undefined);
  const [incomingCellSeed, setIncomingCellSeed] = useState<IncomingNotebookCellSeed | undefined>(
    undefined
  );
  const [notebookSummaries, setNotebookSummaries] = useState<NotebookSummary[]>([]);
  const [activeNotebookId, setActiveNotebookId] = useState<string | null>(null);

  const handleNotebookContextChange = useCallback(
    (nextSummaries: NotebookSummary[], nextActiveId: string | null) => {
      setNotebookSummaries(nextSummaries);
      setActiveNotebookId(nextActiveId);
    },
    []
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("mathlab_theme", theme);
  }, [theme]);

  useEffect(() => {
    fetchHealth()
      .then((res) => {
        setHealth(res);
        setHealthError(null);
      })
      .catch((err) => {
        setHealthError(err instanceof Error ? err.message : "Backend offline");
      });

    fetchOperations()
      .then(setOperations)
      .catch(() => {
        /* Fallback presets remain usable inside ComputeTester */
      });

    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session?.user ?? null);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      const nextUser = session?.user ?? null;
      setUser((prev) => (prev?.id === nextUser?.id ? prev : nextUser));
      if (event === "PASSWORD_RECOVERY") {
        setRecoveryOpen(true);
      }
      if (event === "SIGNED_IN" || event === "SIGNED_OUT") {
        setAuthVersion((v) => v + 1);
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  function handlePlotFromNotebook(seed: Omit<PlotSeed, "seq">) {
    setPlotSeed((prev) => ({
      ...seed,
      seq: (prev?.seq ?? 0) + 1,
    }));
    setActiveTab("visualize");
  }

  function handleSendToNotebook(seed: Omit<IncomingNotebookCellSeed, "seq">) {
    setIncomingCellSeed((prev) => ({
      ...seed,
      seq: (prev?.seq ?? 0) + 1,
    }));
    setActiveTab("notebook");
  }

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)]">
      <ToastContainer />
      <header className="border-b border-[var(--border-hairline)] bg-[var(--bg-surface)]">
        <div className="mx-auto flex max-w-[1380px] flex-wrap items-center justify-between gap-x-2 gap-y-2.5 px-3 py-3 sm:gap-3 sm:px-8 sm:py-3.5">
          <div className="order-1 flex min-w-0 items-center gap-2 sm:gap-2.5">
            <MathLabLogo className="h-8 w-8 shrink-0" />
            <div className="min-w-0 leading-tight">
              <h1 className="text-base font-bold tracking-tight text-[var(--text-primary)] sm:text-lg">
                MathLab
              </h1>
              <p className="truncate text-[11px] text-[var(--text-muted)] sm:text-xs">
                Computational Workbench
              </p>
            </div>
          </div>

          <nav className="order-3 flex w-full overflow-x-auto rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-0.5 text-xs sm:order-4 xl:order-2 xl:ml-3 xl:w-auto xl:text-[13px]">
            {(
              [
                ["notebook", "Notebook"],
                ["compute", "Quick Compute"],
                ["visualize", "Visualization Studio"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setActiveTab(key)}
                className={`flex-1 shrink-0 whitespace-nowrap rounded-sm px-2 py-1.5 text-center font-medium transition sm:px-3.5 xl:flex-initial ${
                  activeTab === key
                    ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>

          <div className="order-2 ml-auto flex items-center gap-1.5 sm:gap-2 xl:order-3 xl:ml-auto">
            <button
              type="button"
              onClick={() => setTheme((prev) => (prev === "light" ? "dark" : "light"))}
              className="shrink-0 whitespace-nowrap rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] sm:px-3"
              title="Switch color theme"
            >
              {theme === "light" ? "☾ Dark" : "☀ Light"}
            </button>

            <div
              title={
                health
                  ? `Connected to math engine (${API_BASE_URL || window.location.origin})`
                  : healthError
                    ? `Offline: ${healthError} (${API_BASE_URL || window.location.origin})`
                    : `Connecting to ${API_BASE_URL || window.location.origin}`
              }
              className="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1.5 text-xs sm:px-3"
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  health ? "bg-emerald-500" : healthError ? "bg-rose-500" : "bg-amber-500"
                }`}
              />
              <span className="text-[var(--text-secondary)]">
                {health ? "Online" : healthError ? "Offline" : "Connecting..."}
              </span>
            </div>
          </div>

          <div className="order-4 flex w-full items-center justify-between gap-2 border-t border-[var(--border-hairline)] pt-2 sm:order-3 sm:w-auto sm:border-0 sm:pt-0 xl:order-4">
            <AuthPanel
              user={user}
              onAuthChanged={() => setAuthVersion((v) => v + 1)}
              recoveryOpen={recoveryOpen}
              onCloseRecovery={() => setRecoveryOpen(false)}
            />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1380px] px-4 py-5 sm:px-8 sm:py-7">
        <div className={activeTab === "notebook" ? "" : "hidden"}>
          <NotebookWorkbench
            operations={operations}
            authKey={`${user?.id ?? "guest"}-${authVersion}`}
            isAuthenticated={Boolean(user)}
            onPlotExpression={handlePlotFromNotebook}
            incomingCellSeed={incomingCellSeed}
            onNotebookContextChange={handleNotebookContextChange}
          />
        </div>
        {activeTab === "compute" && (
          <Suspense
            fallback={
              <div className="py-12 text-center font-mono text-xs text-[var(--text-muted)]">
                Loading Quick Compute...
              </div>
            }
          >
            <ComputeTester
              operations={operations}
              onPlotExpression={handlePlotFromNotebook}
              onSendToNotebook={handleSendToNotebook}
              notebookSummaries={notebookSummaries}
              activeNotebookId={activeNotebookId}
            />
          </Suspense>
        )}
        {activeTab === "visualize" && (
          <Suspense
            fallback={
              <div className="py-12 text-center font-mono text-xs text-[var(--text-muted)]">
                Loading Visualization Studio...
              </div>
            }
          >
            <VisualizationStudio plotSeed={plotSeed} theme={theme} />
          </Suspense>
        )}
      </main>
    </div>
  );
}
