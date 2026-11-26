interface MathLabLogoProps {
  className?: string;
}

/** Crisp geometric coordinate mark for the MathLab workbench header. */
export function MathLabLogo({ className = "h-8 w-8" }: MathLabLogoProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <rect width="32" height="32" rx="7" fill="var(--accent-ink)" />
      <path
        d="M16 5.5v21M5.5 16h21"
        stroke="var(--accent-ink-fg)"
        strokeOpacity="0.16"
        strokeWidth="1"
        strokeLinecap="round"
      />
      <path
        d="M8.25 22.25V10.5L16 17.75 23.75 10.5v11.75"
        stroke="var(--accent-ink-fg)"
        strokeWidth="2.35"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="23.75" cy="10.5" r="2.2" fill="#10b981" />
    </svg>
  );
}
