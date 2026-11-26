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
        <div className="mx-auto flex max-w-[1380px] flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-8">
          <div className="flex min-w-0 flex-wrap items-center gap-3 sm:gap-6">
            <div className="flex items-center gap-2.5">
              <MathLabLogo className="h-8 w-8 shrink-0" />
              <div className="leading-tight">
                <h1 className="text-lg font-bold tracking-tight text-[var(--text-primary)]">
                  MathLab
                </h1>
                <p className="text-xs text-[var(--text-muted)]">Computational Workbench</p>
              </div>
            </div>

            <nav className="flex max-w-full overflow-x-auto rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-0.5 text-xs sm:text-[13px]">
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
                  className={`shrink-0 rounded-sm px-3 py-1.5 font-medium transition sm:px-3.5 ${
                    activeTab === key
                      ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  {label}
                </button>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setTheme((prev) => (prev === "light" ? "dark" : "light"))}
              className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
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
              className="flex items-center gap-1.5 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 text-xs"
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
