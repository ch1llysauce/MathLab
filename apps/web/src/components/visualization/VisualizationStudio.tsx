import { FormEvent, useEffect, useRef, useState } from "react";

import { ApiClientError, fetchPlot } from "../../services/api";
import type { PlotResponse, PlotSeed } from "../../types/compute";
import {
  backspaceInputElement,
  formatAsciiMathPreview,
  insertIntoInputElement,
} from "../../utils/mathPreview";
import { ErrorAlert } from "../common/ErrorAlert";
import { MathKeypad } from "../common/MathKeypad";
import {
  MatrixGridEditor,
  type MatrixData,
  normalizeMatrixData,
  normalizeVectorData,
  VectorGridEditor,
} from "../common/MatrixGridEditor";
import { showToast } from "../common/Toast";
import { LatexBlock } from "../computation/LatexBlock";
import { PlotlyChart } from "./PlotlyChart";

type StudioPlotMode = "2d" | "3d" | "matrix";
type MatrixViewMode = "auto" | "transform" | "system" | "surface" | "heatmap";

interface VizPreset {
  label: string;
  plotType: StudioPlotMode;
  expression: string;
  compareExpr: string;
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
  includeDerivative: boolean;
  includeIntegral: boolean;
  tangentAt: string;
  paramName: string;
  paramValue: number;
  matrix?: MatrixData;
  vector?: (number | string)[];
  matrixView?: MatrixViewMode;
}

const PRESETS: VizPreset[] = [
  {
    label: "Parabola + Tangent",
    plotType: "2d",
    expression: "x^2 - 4",
    compareExpr: "",
    xMin: -5,
    xMax: 5,
    yMin: -5,
    yMax: 5,
    includeDerivative: true,
    includeIntegral: false,
    tangentAt: "1",
    paramName: "",
    paramValue: 1,
  },
  {
    label: "Trig Comparison",
    plotType: "2d",
    expression: "sin(a*x)",
    compareExpr: "cos(a*x)",
    xMin: -6.28,
    xMax: 6.28,
    yMin: -5,
    yMax: 5,
    includeDerivative: false,
    includeIntegral: false,
    tangentAt: "",
    paramName: "a",
    paramValue: 1,
  },
  {
    label: "Integral Area",
    plotType: "2d",
    expression: "exp(-x^2)",
    compareExpr: "",
    xMin: -3,
    xMax: 3,
    yMin: -5,
    yMax: 5,
    includeDerivative: false,
    includeIntegral: true,
    tangentAt: "",
    paramName: "",
    paramValue: 1,
  },
  {
    label: "3D Surface",
    plotType: "3d",
    expression: "sin(x)*cos(y)",
    compareExpr: "",
    xMin: -4,
    xMax: 4,
    yMin: -4,
    yMax: 4,
    includeDerivative: false,
    includeIntegral: false,
    tangentAt: "",
    paramName: "",
    paramValue: 1,
  },
  {
    label: "2×2 Matrix Transform",
    plotType: "matrix",
    expression: "",
    compareExpr: "",
    xMin: -5,
    xMax: 5,
    yMin: -5,
    yMax: 5,
    includeDerivative: false,
    includeIntegral: false,
    tangentAt: "",
    paramName: "",
    paramValue: 1,
    matrix: [[2, 1], [0, 2]],
    matrixView: "transform",
  },
  {
    label: "2×2 System (Ax = b)",
    plotType: "matrix",
    expression: "",
    compareExpr: "",
    xMin: -5,
    xMax: 5,
    yMin: -5,
    yMax: 5,
    includeDerivative: false,
    includeIntegral: false,
    tangentAt: "",
    paramName: "",
    paramValue: 1,
    matrix: [[2, 1], [1, -1]],
    vector: [5, 1],
    matrixView: "system",
  },
];

interface VisualizationStudioProps {
  plotSeed?: PlotSeed;
  theme: "light" | "dark";
}

function resolveRangeInputs(
  minRaw: string,
  maxRaw: string,
  fallbackSpan = 20
): [number, number] | null {
  const minClean = minRaw.trim();
  const maxClean = maxRaw.trim();
  if (!minClean && !maxClean) {
    return [-fallbackSpan / 2, fallbackSpan / 2];
  }
  if (!minClean && maxClean) {
    const hi = Number(maxClean);
    return Number.isFinite(hi) ? [hi - fallbackSpan, hi] : null;
  }
  if (minClean && !maxClean) {
    const lo = Number(minClean);
    return Number.isFinite(lo) ? [lo, lo + fallbackSpan] : null;
  }
  const lo = Number(minClean);
  const hi = Number(maxClean);
  if (!Number.isFinite(lo) || !Number.isFinite(hi) || lo >= hi) {
    return null;
  }
  return [lo, hi];
}

export function VisualizationStudio({ plotSeed, theme }: VisualizationStudioProps) {
  const primaryInputRef = useRef<HTMLInputElement | null>(null);
  const [keypadOpen, setKeypadOpen] = useState(false);
  const [plotType, setPlotType] = useState<StudioPlotMode>("2d");
  const [expression, setExpression] = useState(plotSeed?.expr || "x^2 - 4");
  const [compareExpr, setCompareExpr] = useState(plotSeed?.compareExpr || "");
  const [plotVar, setPlotVar] = useState(plotSeed?.variable || "x");
  const [xMin, setXMin] = useState("-5");
  const [xMax, setXMax] = useState("5");
  const [yMin, setYMin] = useState("-5");
  const [yMax, setYMax] = useState("5");
  const [plottedXRange, setPlottedXRange] = useState<[number, number]>([-5, 5]);
  const [includeDerivative, setIncludeDerivative] = useState(true);
  const [includeIntegral, setIncludeIntegral] = useState(false);
  const [tangentAt, setTangentAt] = useState("1");
  const [tangentY, setTangentY] = useState("0");
  const [paramName, setParamName] = useState("");
  const [paramValue, setParamValue] = useState(1);

  const [matrixData, setMatrixData] = useState<MatrixData>([[2, 1], [0, 2]]);
  const [matrixBData, setMatrixBData] = useState<MatrixData>([[1, 0], [0, 1]]);
  const [useMatrixB, setUseMatrixB] = useState(false);
  const [vectorData, setVectorData] = useState<(number | string)[]>([5, 1]);
  const [matrixView, setMatrixView] = useState<MatrixViewMode>("auto");

  const [loading, setLoading] = useState(false);
  const [plotData, setPlotData] = useState<PlotResponse | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);

  useEffect(() => {
    if (!plotSeed) return;

    if (plotSeed.plotType === "matrix" || plotSeed.matrix) {
      const nextMat = normalizeMatrixData(plotSeed.matrix);
      const nextView = plotSeed.matrixView ?? (plotSeed.vector ? "system" : "auto");
      const nextVec = plotSeed.vector
        ? normalizeVectorData(plotSeed.vector, nextMat.length)
        : normalizeVectorData(undefined, nextMat.length);
      const hasCompare = Boolean(plotSeed.matrixB);
      const nextMatB = plotSeed.matrixB
        ? normalizeMatrixData(plotSeed.matrixB)
        : normalizeMatrixData(undefined, nextMat.length, nextMat[0]?.length ?? 2);

      setPlotType("matrix");
      setMatrixData(nextMat);
      setVectorData(nextVec);
      setMatrixBData(nextMatB);
      setUseMatrixB(hasCompare);
      setMatrixView(nextView);
      setError(null);
      setLoading(true);
      fetchPlot({
        plot_type: "matrix",
        variables: ["x", "y"],
        matrix: nextMat,
        matrix_b: hasCompare ? nextMatB : undefined,
        vector: nextView === "system" || plotSeed.vector ? nextVec : undefined,
        matrix_view: nextView,
      })
        .then(setPlotData)
        .catch((err) => {
          setError({
            code: err instanceof ApiClientError ? err.code : "PLOT_ERROR",
            message: err instanceof Error ? err.message : "Failed to plot matrix.",
          });
        })
        .finally(() => setLoading(false));
      return;
    }

    if (plotSeed.expr) {
      const nextCompare = plotSeed.compareExpr || "";
      const nextVar = plotSeed.variable || "x";
      const nextIncludeDeriv = !nextCompare;
      setPlotType("2d");
      setExpression(plotSeed.expr);
      setCompareExpr(nextCompare);
      setPlotVar(nextVar);
      setXMin("-5");
      setXMax("5");
      setPlottedXRange([-5, 5]);
      setParamName("");
      setIncludeDerivative(nextIncludeDeriv);
      setIncludeIntegral(false);
      setTangentAt("");
      setError(null);
      setLoading(true);
      fetchPlot({
        plot_type: "2d",
        expressions: [plotSeed.expr, nextCompare].filter(Boolean),
        variables: [nextVar],
        x_range: [-5, 5],
        include_derivative: nextIncludeDeriv,
        detect_features: true,
      })
        .then(setPlotData)
        .catch((err) => {
          setError({
            code: err instanceof ApiClientError ? err.code : "PLOT_ERROR",
            message: err instanceof Error ? err.message : "Failed to plot expression.",
          });
        })
        .finally(() => setLoading(false));
    }
  }, [plotSeed]);

  async function runPlot(
    overrideParamVal?: number,
    overrideXRange?: [number, number],
    overridePlotType?: StudioPlotMode,
    overrideMatrixView?: MatrixViewMode
  ) {
    const activePlotType = overridePlotType ?? plotType;
    const activeMatView = overrideMatrixView ?? matrixView;
    setError(null);

    const activeParamValue = overrideParamVal ?? paramValue;
    const parameters: Record<string, number> =
      paramName.trim() !== "" ? { [paramName.trim()]: activeParamValue } : {};

    if (activePlotType === "matrix") {
      setLoading(true);
      try {
        const data = await fetchPlot({
          plot_type: "matrix",
          variables: ["x", "y"],
          matrix: matrixData,
          matrix_b: useMatrixB ? matrixBData : undefined,
          vector:
            activeMatView === "system"
              ? normalizeVectorData(vectorData, matrixData.length)
              : undefined,
          matrix_view: activeMatView,
          parameters,
        });
        setPlotData(data);
        if (overrideParamVal === undefined && overrideXRange === undefined) {
          showToast("Matrix plot rendered", { variant: "success" });
        }
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError({ code: err.code, message: err.message });
          showToast(err.message, { variant: "error" });
        } else {
          const msg = err instanceof Error ? err.message : "Failed to generate matrix plot.";
          setError({ code: "NETWORK_ERROR", message: msg });
          showToast(msg, { variant: "error" });
        }
      } finally {
        setLoading(false);
      }
      return;
    }

    const resolvedX = overrideXRange ?? resolveRangeInputs(xMin, xMax, 20);
    if (!resolvedX) {
      setError({
        code: "INVALID_RANGE",
        message: "x range must have min < max (or leave both blank for Auto).",
      });
      return;
    }

    let resolvedY: [number, number] | undefined = undefined;
    if (activePlotType === "3d") {
      const candidateY = resolveRangeInputs(yMin, yMax, 10);
      if (!candidateY) {
        setError({
          code: "INVALID_RANGE",
          message: "y range must have min < max (or leave both blank for Auto).",
        });
        return;
      }
      resolvedY = candidateY;
    }

    setLoading(true);
    const expressions = [expression.trim(), compareExpr.trim()].filter(Boolean);

    try {
      const data = await fetchPlot({
        plot_type: activePlotType,
        expressions,
        variables: activePlotType === "3d" ? ["x", "y"] : [plotVar || "x"],
        x_range: resolvedX,
        y_range: resolvedY,
        parameters,
        include_derivative: includeDerivative,
        include_integral: activePlotType === "2d" && includeIntegral,
        tangent_at: tangentAt.trim() !== "" ? Number(tangentAt) : null,
        tangent_y:
          activePlotType === "3d" && tangentY.trim() !== "" ? Number(tangentY) : null,
        detect_features: activePlotType === "2d",
      });
      setPlottedXRange(resolvedX);
      setPlotData(data);
      if (overrideParamVal === undefined && overrideXRange === undefined) {
        showToast(`${activePlotType.toUpperCase()} plot rendered`, { variant: "success" });
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError({ code: err.code, message: err.message });
        showToast(err.message, { variant: "error" });
      } else {
        const msg = err instanceof Error ? err.message : "Failed to generate plot.";
        setError({
          code: "NETWORK_ERROR",
          message: msg,
        });
        showToast(msg, { variant: "error" });
      }
    } finally {
      setLoading(false);
    }
  }

  function applyPreset(preset: VizPreset) {
    setPlotType(preset.plotType);
    setExpression(preset.expression);
    setCompareExpr(preset.compareExpr);
    setXMin(String(preset.xMin));
    setXMax(String(preset.xMax));
    setYMin(String(preset.yMin));
    setYMax(String(preset.yMax));
    setPlottedXRange([preset.xMin, preset.xMax]);
    setIncludeDerivative(preset.includeDerivative);
    setIncludeIntegral(preset.includeIntegral);
    setTangentAt(preset.tangentAt);
    setParamName(preset.paramName);
    setParamValue(preset.paramValue);
    if (preset.matrix) {
      setMatrixData(preset.matrix);
      setUseMatrixB(false);
    }
    if (preset.vector) {
      setVectorData(preset.vector);
    }
    if (preset.matrixView) {
      setMatrixView(preset.matrixView);
    }
    setError(null);
  }

  function handleSwitchPlotType(nextMode: StudioPlotMode) {
    if (nextMode === plotType) return;
    setPlotType(nextMode);
    if (plotData && (nextMode === "matrix" || expression.trim() !== "")) {
      void runPlot(undefined, undefined, nextMode);
    }
  }

  function handleSwitchMatrixView(nextView: MatrixViewMode) {
    setMatrixView(nextView);
    if (plotData && plotType === "matrix") {
      void runPlot(undefined, undefined, "matrix", nextView);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void runPlot();
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => applyPreset(preset)}
              className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="inline-flex rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-0.5 text-xs">
          {(["2d", "3d", "matrix"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => handleSwitchPlotType(mode)}
              className={`rounded-sm px-3 py-1 font-semibold uppercase ${
                plotType === mode
                  ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-4"
      >
        {plotType === "matrix" ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-1.5 text-xs">
                <span className="mr-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  View:
                </span>
                {(
                  [
                    ["auto", "Auto"],
                    ["transform", "Transform & Vectors (2D/3D/nD)"],
                    ["system", "Linear System (Ax = b)"],
                    ["surface", "3D Surface"],
                    ["heatmap", "Heatmap"],
                  ] as const
                ).map(([val, label]) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => handleSwitchMatrixView(val)}
                    className={`rounded border px-2.5 py-1 text-[11px] font-medium transition ${
                      matrixView === val
                        ? "border-[var(--border-strong)] bg-[var(--bg-subtle)] text-[var(--text-primary)]"
                        : "border-[var(--border-hairline)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--border-strong)]"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {matrixView !== "system" && matrixView !== "heatmap" && matrixView !== "surface" && (
                <label className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                  <input
                    type="checkbox"
                    checked={useMatrixB}
                    onChange={(e) => setUseMatrixB(e.target.checked)}
                  />
                  Compare Matrix B
                </label>
              )}
            </div>

            <div className="flex flex-wrap items-start gap-4">
              <MatrixGridEditor
                label="Matrix A"
                value={matrixData}
                onChange={(nextMat) => {
                  setMatrixData(nextMat);
                  setVectorData((prev) => normalizeVectorData(prev, nextMat.length));
                }}
              />
              {matrixView === "system" && (
                <VectorGridEditor
                  label="Vector b"
                  length={matrixData.length}
                  value={vectorData}
                  onChange={setVectorData}
                />
              )}
              {useMatrixB &&
                matrixView !== "system" &&
                matrixView !== "heatmap" &&
                matrixView !== "surface" && (
                <MatrixGridEditor
                  label="Compare / Result B"
                  value={matrixBData}
                  onChange={setMatrixBData}
                />
              )}
            </div>
          </div>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    {plotType === "3d" ? "Surface f(x, y)" : "Primary Function f(x)"}
                  </label>
                  <button
                    type="button"
                    onClick={() => setKeypadOpen((prev) => !prev)}
                    className="text-[11px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  >
                    {keypadOpen ? "Hide Keypad" : "Keypad"}
                  </button>
                </div>
                <input
                  ref={primaryInputRef}
                  type="text"
                  value={expression}
                  onChange={(e) => setExpression(e.target.value)}
                  className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 font-mono text-sm text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
                />
                {(() => {
                  const preview = formatAsciiMathPreview(expression);
                  if (!preview) return null;
                  return (
                    <div className="flex items-center gap-2 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)]/50 px-2.5 py-0.5 text-xs">
                      <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                        Preview
                      </span>
                      <LatexBlock latex={preview} displayMode={false} />
                    </div>
                  );
                })()}
              </div>

              <div className="space-y-1.5">
                <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  {plotType === "3d"
                    ? "Compare Surface g(x, y) (optional)"
                    : "Compare Function g(x) (optional)"}
                </label>
                <input
                  type="text"
                  value={compareExpr}
                  onChange={(e) => setCompareExpr(e.target.value)}
                  placeholder={plotType === "3d" ? "e.g. x*y" : "e.g. cos(x)"}
                  className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 font-mono text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none"
                />
                {(() => {
                  const preview = formatAsciiMathPreview(compareExpr);
                  if (!preview) return null;
                  return (
                    <div className="flex items-center gap-2 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)]/50 px-2.5 py-0.5 text-xs">
                      <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                        Preview
                      </span>
                      <LatexBlock latex={preview} displayMode={false} />
                    </div>
                  );
                })()}
              </div>
            </div>

            {keypadOpen && (
              <MathKeypad
                onInsert={(text, cursorBack) =>
                  insertIntoInputElement(
                    primaryInputRef.current,
                    expression,
                    text,
                    cursorBack,
                    setExpression
                  )
                }
                onBackspace={() =>
                  backspaceInputElement(primaryInputRef.current, expression, setExpression)
                }
                onClear={() => setExpression("")}
                onRun={() => void runPlot()}
                onClose={() => setKeypadOpen(false)}
              />
            )}

            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 sm:gap-3">
              <div>
                <label className="mb-1 block text-xs text-[var(--text-muted)]">
                  x min <span className="text-[10px] opacity-75">(blank = auto)</span>
                </label>
                <input
                  type="number"
                  step="any"
                  value={xMin}
                  onChange={(e) => setXMin(e.target.value)}
                  placeholder="auto (-10)"
                  className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-[var(--text-muted)]">
                  x max <span className="text-[10px] opacity-75">(blank = auto)</span>
                </label>
                <input
                  type="number"
                  step="any"
                  value={xMax}
                  onChange={(e) => setXMax(e.target.value)}
                  placeholder="auto (10)"
                  className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                />
              </div>

              {plotType === "3d" && (
                <>
                  <div>
                    <label className="mb-1 block text-xs text-[var(--text-muted)]">
                      y min <span className="text-[10px] opacity-75">(blank = auto)</span>
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={yMin}
                      onChange={(e) => setYMin(e.target.value)}
                      placeholder="auto (-5)"
                      className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[var(--text-muted)]">
                      y max <span className="text-[10px] opacity-75">(blank = auto)</span>
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={yMax}
                      onChange={(e) => setYMax(e.target.value)}
                      placeholder="auto (5)"
                      className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                    />
                  </div>
                </>
              )}

              <div>
                <label className="mb-1 block text-xs text-[var(--text-muted)]">Tangent at x₀</label>
                <input
                  type="text"
                  value={tangentAt}
                  onChange={(e) => setTangentAt(e.target.value)}
                  placeholder="optional"
                  className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                />
              </div>

              {plotType === "3d" && (
                <div>
                  <label className="mb-1 block text-xs text-[var(--text-muted)]">Tangent at y₀</label>
                  <input
                    type="text"
                    value={tangentY}
                    onChange={(e) => setTangentY(e.target.value)}
                    placeholder="0"
                    className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                  />
                </div>
              )}

              <div>
                <label className="mb-1 block text-xs text-[var(--text-muted)]">Parameter</label>
                <input
                  type="text"
                  value={paramName}
                  onChange={(e) => setParamName(e.target.value)}
                  placeholder="e.g. a"
                  className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                />
              </div>
            </div>
          </>
        )}

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-[var(--border-hairline)] pt-3">
          <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--text-secondary)]">
            {plotType !== "matrix" && (
              <label className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={includeDerivative}
                  onChange={(e) => setIncludeDerivative(e.target.checked)}
                />
                {plotType === "3d"
                  ? "Partial Derivatives (∂f/∂x, ∂f/∂y)"
                  : "Derivative f'(x)"}
              </label>
            )}
            {plotType === "2d" && (
              <label className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={includeIntegral}
                  onChange={(e) => setIncludeIntegral(e.target.checked)}
                />
                Area under curve
              </label>
            )}

            {plotType !== "matrix" && paramName.trim() !== "" && (
              <label className="flex items-center gap-2">
                <span className="font-mono">
                  {paramName.trim()} = {paramValue.toFixed(1)}
                </span>
                <input
                  type="range"
                  min={-5}
                  max={5}
                  step={0.5}
                  value={paramValue}
                  onChange={(e) => {
                    const nextVal = Number(e.target.value);
                    setParamValue(nextVal);
                    void runPlot(nextVal);
                  }}
                  className="w-28"
                />
              </label>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-[var(--accent-ink)] px-4 py-2 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90 disabled:opacity-60 sm:ml-auto sm:w-auto sm:py-1.5"
          >
            {loading ? "Plotting..." : "Render Plot"}
          </button>
        </div>
      </form>

      {error && <ErrorAlert code={error.code} message={error.message} />}

      {plotData && (
        <div className="space-y-4">
          <PlotlyChart
            traces={plotData.traces}
            plotType={plotData.plot_type}
            theme={theme}
            plottedXRange={plottedXRange}
            equalAspect={Boolean(plotData.metadata?.equal_aspect)}
            onExpandRange={
              plotData.metadata?.matrix_view
                ? undefined
                : (nextMin, nextMax) => {
                    void runPlot(undefined, [nextMin, nextMax]);
                  }
            }
            onResetRange={
              plotData.metadata?.matrix_view
                ? undefined
                : () => {
                    const resetBounds = resolveRangeInputs(xMin, xMax, 20) ?? [-10, 10];
                    void runPlot(undefined, resetBounds);
                  }
            }
            layoutMeta={plotData.layout}
          />

          {plotData.key_points.length > 0 && (
            <div className="rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-4">
              <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Detected Key Points
              </h3>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                {plotData.key_points.map((pt, idx) => (
                  <div
                    key={`${pt.kind}-${idx}`}
                    className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 text-xs"
                  >
                    <div className="font-semibold uppercase text-[var(--text-primary)]">
                      {pt.kind.replace(/_/g, " ")}
                    </div>
                    <div className="font-mono text-[var(--text-secondary)]">
                      ({pt.x}, {pt.y})
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
