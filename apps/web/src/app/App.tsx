import { useEffect, useState } from "react";

import { ComputeTester } from "../components/computation/ComputeTester";
import { API_BASE_URL, fetchHealth, fetchOperations } from "../services/api";
import type { HealthResponse, OperationInfo } from "../types/compute";

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [operations, setOperations] = useState<OperationInfo[]>([]);

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
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/60">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-3 px-6 py-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">MathLab</h1>
            <p className="text-xs text-slate-400">
              M1 Computation Engine Tester · API: <code>{API_BASE_URL}</code>
            </p>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-slate-800 bg-slate-950 px-3 py-1 text-xs">
            <span
              className={`h-2 w-2 rounded-full ${
                health ? "bg-emerald-400" : healthError ? "bg-rose-400" : "bg-amber-400"
              }`}
            />
            {health ? (
              <span className="text-emerald-300">
                API {health.status} ({health.environment})
              </span>
            ) : (
              <span className="text-rose-300">{healthError ?? "Checking backend..."}</span>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        <ComputeTester operations={operations} />
      </main>
    </div>
  );
}
