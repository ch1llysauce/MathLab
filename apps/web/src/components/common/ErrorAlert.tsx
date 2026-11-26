const ERROR_TITLES: Record<string, string> = {
  INVALID_EXPRESSION: "Check your expression",
  UNSUPPORTED_OPERATION: "Unsupported operation",
  MATHEMATICAL_DOMAIN_ERROR: "Math domain issue",
  COMPUTATION_LIMIT_EXCEEDED: "Calculation limit reached",
  VALIDATION_ERROR: "Check your inputs",
  UNAUTHORIZED: "Sign in required",
  FORBIDDEN: "Access denied",
  NOT_FOUND: "Not found",
  PROXY_NOT_CONFIGURED: "Backend not configured",
  HTTP_ERROR: "Request failed",
  API_ERROR: "Connection issue",
};

function formatHumanMessage(message: string): string {
  const trimmed = message.trim();
  if (!trimmed || trimmed === "Failed to fetch") {
    return "Couldn't reach the math engine right now. Please try again in a few seconds.";
  }
  return trimmed;
}

interface ErrorAlertProps {
  code?: string;
  message: string;
}

/** Human-friendly error banner translating backend error codes into plain-English headings. */
export function ErrorAlert({ code, message }: ErrorAlertProps) {
  const title = (code && ERROR_TITLES[code]) || "Something went wrong";

  return (
    <div className="rounded border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-[var(--status-error)]">
      <div className="font-semibold">{title}</div>
      <p className="mt-0.5 leading-relaxed">{formatHumanMessage(message)}</p>
    </div>
  );
}
