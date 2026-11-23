import katex from "katex";

interface LatexBlockProps {
  latex: string;
  displayMode?: boolean;
}

export function LatexBlock({ latex, displayMode = true }: LatexBlockProps) {
  let html = "";
  let renderError: string | null = null;

  try {
    html = katex.renderToString(latex, {
      displayMode,
      throwOnError: false,
      strict: false,
    });
  } catch (err) {
    renderError = err instanceof Error ? err.message : "Failed to render LaTeX";
  }

  if (renderError) {
    return <code className="text-sm text-amber-300">{latex}</code>;
  }

  return (
    <div
      className="overflow-x-auto py-1 text-lg text-slate-50"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
