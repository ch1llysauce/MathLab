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
    return <code className="text-sm text-amber-600 dark:text-amber-400">{latex}</code>;
  }

  return (
    <div
      className="overflow-x-auto overflow-y-hidden py-1.5 text-base leading-normal text-[var(--text-primary)]"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
