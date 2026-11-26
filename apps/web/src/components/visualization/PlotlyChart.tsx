import { useEffect, useMemo, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";

import {
  formatPlotlyTitleHtml,
  formatPlotlyTraceName,
} from "../../utils/mathPreview";

interface PlotlyChartProps {
  traces: Record<string, unknown>[];
  plotType: "2d" | "3d";
  theme: "light" | "dark";
  plottedXRange?: [number, number];
  equalAspect?: boolean;
  onExpandRange?: (nextMin: number, nextMax: number) => void;
  onResetRange?: () => void;
  layoutMeta: {
    title: string;
    xaxis_title: string;
    yaxis_title: string;
    zaxis_title?: string | null;
  };
}

interface PlotElementWithLayout extends HTMLDivElement {
  _fullLayout?: {
    xaxis?: { range?: [number, number] };
    yaxis?: { range?: [number, number] };
  };
  on?: (eventName: string, handler: (data: Record<string, unknown>) => void) => void;
  removeAllListeners?: (eventName: string) => void;
}

const MAX_AUTO_SPAN = 90000;

export function PlotlyChart({
  traces,
  plotType,
  theme,
  plottedXRange,
  equalAspect = false,
  onExpandRange,
  onResetRange,
  layoutMeta,
}: PlotlyChartProps) {
  const containerRef = useRef<PlotElementWithLayout | null>(null);
  const [dragMode, setDragMode] = useState<"pan" | "zoom">("pan");
  const [isCompact, setIsCompact] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth < 640 : false
  );
  const preservedCameraRef = useRef<{
    x?: [number, number];
    y?: [number, number];
  } | null>(null);
  const lastSignatureRef = useRef<string>("");
  const debounceRef = useRef<number | null>(null);
  const onExpandRef = useRef(onExpandRange);
  const plottedRangeRef = useRef(plottedXRange);

  onExpandRef.current = onExpandRange;
  plottedRangeRef.current = plottedXRange;

  const formattedTraces = useMemo(
    () =>
      traces.map((trace) => {
        let next =
          typeof trace.name === "string"
            ? { ...trace, name: formatPlotlyTraceName(trace.name) }
            : trace;
        if (plotType === "3d" && next.type === "surface" && next.showscale !== false) {
          const existingBar =
            next.colorbar && typeof next.colorbar === "object"
              ? (next.colorbar as Record<string, unknown>)
              : {};
          next = {
            ...next,
            colorbar: {
              ...existingBar,
              thickness: isCompact ? 10 : 18,
              len: isCompact ? 0.52 : 0.78,
              x: isCompact ? 1.01 : 1.02,
              tickfont: { size: isCompact ? 10 : 12 },
            },
          };
        }
        return next;
      }),
    [traces, plotType, isCompact]
  );

  const formattedTitle = useMemo(
    () => formatPlotlyTitleHtml(layoutMeta.title),
    [layoutMeta.title]
  );

  // Reset preserved camera only when the expression/title itself changes (new plot), not on domain resample.
  const plotSignature = `${plotType}::${layoutMeta.title}`;
  if (lastSignatureRef.current !== plotSignature) {
    lastSignatureRef.current = plotSignature;
    preservedCameraRef.current = null;
  }

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const isDark = theme === "dark";
    const bg = isDark ? "#111113" : "#ffffff";
    const grid = isDark ? "#27272a" : "#e4e4e7";
    const zero = isDark ? "#52525b" : "#a1a1aa";
    const ink = isDark ? "#f4f4f5" : "#18181b";

    const cam = preservedCameraRef.current;
    const commonFont = { color: ink, family: "ui-sans-serif, system-ui, sans-serif" };
    const hoverLabelStyle = {
      bgcolor: bg,
      bordercolor: zero,
      font: { color: ink, size: 12, family: "ui-sans-serif, system-ui, sans-serif" },
      namelength: -1,
    };
    const layout: Partial<Plotly.Layout> =
      plotType === "3d"
        ? {
            paper_bgcolor: bg,
            plot_bgcolor: bg,
            font: commonFont,
            hoverlabel: hoverLabelStyle,
            margin: isCompact
              ? { l: 4, r: 4, t: 34, b: 14 }
              : { l: 10, r: 10, t: 36, b: 10 },
            title: { text: formattedTitle, font: { size: isCompact ? 13 : 14, color: ink } },
            scene: {
              xaxis: {
                title: { text: `<i>${layoutMeta.xaxis_title}</i>` },
                gridcolor: grid,
                tickfont: { size: isCompact ? 10 : 11 },
              },
              yaxis: {
                title: { text: `<i>${layoutMeta.yaxis_title}</i>` },
                gridcolor: grid,
                tickfont: { size: isCompact ? 10 : 11 },
              },
              zaxis: {
                title: { text: `<i>${layoutMeta.zaxis_title ?? "z"}</i>` },
                gridcolor: grid,
                tickfont: { size: isCompact ? 10 : 11 },
              },
              camera: {
                eye: isCompact ? { x: 1.55, y: 1.55, z: 1.3 } : { x: 1.3, y: 1.3, z: 1.2 },
              },
            },
            legend: {
              orientation: "h",
              x: 0,
              xanchor: "left",
              y: -0.04,
              yanchor: "top",
              font: { size: isCompact ? 11 : 12 },
            },
          }
        : {
            paper_bgcolor: bg,
            plot_bgcolor: bg,
            font: commonFont,
            hoverlabel: hoverLabelStyle,
            dragmode: dragMode,
            margin: isCompact
              ? { l: 42, r: 12, t: 36, b: 64 }
              : { l: 52, r: 20, t: 38, b: 56 },
            title: { text: formattedTitle, font: { size: isCompact ? 13 : 14, color: ink } },
            xaxis: {
              title: {
                text: `<i>${layoutMeta.xaxis_title}</i>`,
                standoff: isCompact ? 6 : 10,
              },
              automargin: true,
              gridcolor: grid,
              zerolinecolor: zero,
              ...(cam?.x ? { range: cam.x, autorange: false } : {}),
            },
            yaxis: {
              title: {
                text: `<i>${layoutMeta.yaxis_title}</i>`,
                standoff: isCompact ? 4 : 8,
              },
              automargin: true,
              gridcolor: grid,
              zerolinecolor: zero,
              ...(equalAspect ? { scaleanchor: "x", scaleratio: 1 } : {}),
              ...(cam?.y ? { range: cam.y, autorange: false } : {}),
            },
            legend: {
              orientation: "h",
              x: 0,
              xanchor: "left",
              y: isCompact ? -0.26 : -0.18,
              yanchor: "top",
              font: { size: isCompact ? 11 : 12 },
            },
          };

    void Plotly.react(el, formattedTraces as Plotly.Data[], layout, {
      responsive: true,
      displayModeBar: false,
      scrollZoom: true,
    });

    if (plotType === "2d" && el.on) {
      el.removeAllListeners?.("plotly_relayout");
      el.on("plotly_relayout", (eventData: Record<string, unknown>) => {
        const hasAxisUpdate =
          "xaxis.range[0]" in eventData ||
          "xaxis.range" in eventData ||
          "yaxis.range[0]" in eventData ||
          "yaxis.range" in eventData;
        if (!hasAxisUpdate) return;

        const curX = el._fullLayout?.xaxis?.range;
        const curY = el._fullLayout?.yaxis?.range;
        if (!curX || !curY) return;

        preservedCameraRef.current = { x: [curX[0], curX[1]], y: [curY[0], curY[1]] };

        const sampled = plottedRangeRef.current;
        const expandCb = onExpandRef.current;
        if (!sampled || !expandCb) return;

        const visSpan = curX[1] - curX[0];
        const sampledSpan = sampled[1] - sampled[0];
        const edgeBuffer = visSpan * 0.08;
        const needsWider =
          curX[0] < sampled[0] + edgeBuffer || curX[1] > sampled[1] - edgeBuffer;
        const needsHigherDetail = visSpan < sampledSpan * 0.45 && visSpan > 1e-4;

        if (!needsWider && !needsHigherDetail) return;

        if (debounceRef.current !== null) {
          window.clearTimeout(debounceRef.current);
        }
        debounceRef.current = window.setTimeout(() => {
          const pad = Math.min(visSpan * 0.25, (MAX_AUTO_SPAN - visSpan) / 2);
          const nextMin = curX[0] - Math.max(pad, 0);
          const nextMax = curX[1] + Math.max(pad, 0);
          if (nextMax - nextMin <= MAX_AUTO_SPAN && nextMax > nextMin) {
            expandCb(
              Math.round(nextMin * 1000) / 1000,
              Math.round(nextMax * 1000) / 1000
            );
          }
        }, 180);
      });
    }

    const handleResize = () => {
      setIsCompact(window.innerWidth < 640);
      Plotly.Plots.resize(el);
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
      }
      el.removeAllListeners?.("plotly_relayout");
    };
  }, [formattedTraces, formattedTitle, plotType, theme, layoutMeta, dragMode, equalAspect, isCompact]);

  function handleModeChange(nextMode: "pan" | "zoom") {
    setDragMode(nextMode);
    if (containerRef.current && plotType === "2d") {
      void Plotly.relayout(containerRef.current, { dragmode: nextMode });
    }
  }

  function scaleAxis(range: [number, number], factor: number): [number, number] {
    const center = (range[0] + range[1]) / 2;
    const half = ((range[1] - range[0]) / 2) * factor;
    return [center - half, center + half];
  }

  function handleZoom(factor: number) {
    const el = containerRef.current;
    if (!el || plotType !== "2d") return;
    const xRange = el._fullLayout?.xaxis?.range;
    const yRange = el._fullLayout?.yaxis?.range;
    if (!xRange || !yRange) return;

    const nextX = scaleAxis(xRange, factor);
    const nextY = scaleAxis(yRange, factor);
    preservedCameraRef.current = { x: nextX, y: nextY };

    void Plotly.relayout(el, {
      "xaxis.range": nextX,
      "yaxis.range": nextY,
    });
  }

  function handleReset() {
    const el = containerRef.current;
    if (!el) return;
    if (plotType === "3d") {
      void Plotly.relayout(el, {
        "scene.camera": { eye: { x: 1.25, y: 1.25, z: 1.25 } },
      });
      return;
    }
    preservedCameraRef.current = null;
    if (onResetRange) {
      onResetRange();
      return;
    }
    void Plotly.relayout(el, {
      "xaxis.autorange": true,
      "yaxis.autorange": true,
    });
  }

  async function handleDownload(format: "png" | "svg") {
    if (!containerRef.current) return;
    await Plotly.downloadImage(containerRef.current, {
      format,
      width: 1200,
      height: 750,
      filename: "mathlab-plot",
    });
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        {plotType === "2d" ? (
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-0.5 text-[11px]">
              <button
                type="button"
                onClick={() => handleModeChange("pan")}
                title="Drag graph freely in any direction"
                className={`rounded-sm px-2.5 py-0.5 font-medium ${
                  dragMode === "pan"
                    ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                Pan
              </button>
              <button
                type="button"
                onClick={() => handleModeChange("zoom")}
                title="Draw a rectangle to zoom into a region"
                className={`rounded-sm px-2.5 py-0.5 font-medium ${
                  dragMode === "zoom"
                    ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                Box Zoom
              </button>
            </div>

            <div className="inline-flex items-center overflow-hidden rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] text-[11px]">
              <button
                type="button"
                onClick={() => handleZoom(0.6)}
                title="Zoom in around center"
                className="border-r border-[var(--border-hairline)] px-2.5 py-1 font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
              >
                Zoom In +
              </button>
              <button
                type="button"
                onClick={() => handleZoom(1.65)}
                title="Zoom out and dynamically extend curve"
                className="border-r border-[var(--border-hairline)] px-2.5 py-1 font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
              >
                Zoom Out −
              </button>
              <button
                type="button"
                onClick={handleReset}
                title="Reset view to default domain"
                className="px-2.5 py-1 text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
              >
                Reset View
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
            <span>Drag to rotate · Scroll to zoom</span>
            <button
              type="button"
              onClick={handleReset}
              className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              Reset View
            </button>
          </div>
        )}

        <div className="flex items-center gap-1.5 text-[11px]">
          <button
            type="button"
            onClick={() => void handleDownload("png")}
            className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
          >
            Save PNG
          </button>
          <button
            type="button"
            onClick={() => void handleDownload("svg")}
            className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 py-1 font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
          >
            Save SVG
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className={`w-full rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] ${
          plotType === "3d" ? "h-[410px] sm:h-[460px]" : "h-[380px] sm:h-[440px]"
        }`}
      />
    </div>
  );
}
