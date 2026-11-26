import { type FormEvent, type ReactNode, useState } from "react";
import type { User } from "@supabase/supabase-js";

import { Modal } from "../../components/common/Modal";
import { showToast } from "../../components/common/Toast";
import { isSupabaseConfigured, supabase } from "../../services/supabase";

interface AuthPanelProps {
  user: User | null;
  onAuthChanged: () => void;
  recoveryOpen?: boolean;
  onCloseRecovery?: () => void;
}

type AuthMode = "signin" | "signup" | "forgot";

interface PasswordInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  minLength?: number;
  labelAction?: ReactNode;
}

function PasswordInput({ label, value, onChange, minLength = 6, labelAction }: PasswordInputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <label className="block text-xs text-[var(--text-secondary)]">{label}</label>
        {labelAction}
      </div>
      <div className="relative">
        <input
          type={visible ? "text" : "password"}
          required
          minLength={minLength}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] py-2 pr-9 pl-3 text-sm text-[var(--text-primary)] focus:border-[var(--border-strong)] focus:outline-none"
        />
        <button
          type="button"
          onClick={() => setVisible((prev) => !prev)}
          aria-label={visible ? "Hide password" : "Show password"}
          className="absolute inset-y-0 right-0 flex items-center px-2.5 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
        >
          {visible ? (
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
              <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function ErrorCard({ message, className = "" }: { message: string | null; className?: string }) {
  if (!message) return null;
  return (
    <div
      className={`rounded border border-rose-500/40 bg-rose-500/10 p-2 text-xs text-[var(--status-error)] ${className}`.trim()}
    >
      {message}
    </div>
  );
}

export function AuthPanel({
  user,
  onAuthChanged,
  recoveryOpen = false,
  onCloseRecovery,
}: AuthPanelProps) {
  const [open, setOpen] = useState(false);
  const [confirmSignOutOpen, setConfirmSignOutOpen] = useState(false);
  const [mode, setMode] = useState<AuthMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [recoveryError, setRecoveryError] = useState<string | null>(null);
  const [recoveryLoading, setRecoveryLoading] = useState(false);

  if (!isSupabaseConfigured || !supabase) {
    return (
      <span
        title="Configure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env to enable user sign-in"
        className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 text-xs text-[var(--text-secondary)]"
      >
        Guest Mode
      </span>
    );
  }

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setPassword("");
    setEmailError(null);
    setError(null);
    setMessage(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setEmailError(null);
    setError(null);
    setMessage(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setEmailError("Please enter your email address.");
      return;
    }
    if (!isValidEmail(trimmedEmail)) {
      setEmailError("Please enter a valid email address (e.g. name@example.com).");
      return;
    }
    if (mode !== "forgot" && password.length < 6) {
      setError(
        password.length === 0
          ? "Please enter your password."
          : "Password must be at least 6 characters."
      );
      return;
    }

    setLoading(true);

    try {
      if (mode === "signin") {
        const { error: signInErr } = await supabase.auth.signInWithPassword({
          email: trimmedEmail,
          password,
        });
        if (signInErr) throw signInErr;
        setOpen(false);
        showToast("Signed in", { detail: trimmedEmail, variant: "success" });
        onAuthChanged();
      } else if (mode === "signup") {
        const { error: signUpErr } = await supabase.auth.signUp({
          email: trimmedEmail,
          password,
        });
        if (signUpErr) throw signUpErr;
        setMessage("Check your email for confirmation or sign in if auto-confirm is enabled.");
        showToast("Account created", { detail: trimmedEmail, variant: "info" });
      } else {
        const { error: resetErr } = await supabase.auth.resetPasswordForEmail(trimmedEmail, {
          redirectTo: window.location.origin,
        });
        if (resetErr) throw resetErr;
        setMessage("Check your email for a password reset link.");
        showToast("Reset link sent", { detail: trimmedEmail, variant: "info" });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Authentication failed.";
      setError(msg);
      showToast(msg, { variant: "error" });
    } finally {
      setLoading(false);
    }
  }

  async function handlePasswordUpdate(e: FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setRecoveryError(null);

    if (newPassword.length < 6) {
      setRecoveryError(
        newPassword.length === 0
          ? "Please enter a new password."
          : "Password must be at least 6 characters."
      );
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setRecoveryError("Passwords do not match.");
      return;
    }

    setRecoveryLoading(true);
    try {
      const { error: updateErr } = await supabase.auth.updateUser({ password: newPassword });
      if (updateErr) throw updateErr;
      setNewPassword("");
      setConfirmNewPassword("");
      onCloseRecovery?.();
      showToast("Password updated", { variant: "success" });
      onAuthChanged();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to update password.";
      setRecoveryError(msg);
      showToast(msg, { variant: "error" });
    } finally {
      setRecoveryLoading(false);
    }
  }

  async function handleSignOut() {
    if (!supabase) return;
    setLoading(true);
    try {
      await supabase.auth.signOut();
      setConfirmSignOutOpen(false);
      showToast("Signed out", { variant: "info" });
      onAuthChanged();
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleSignIn() {
    if (!supabase) return;
    setError(null);
    setMessage(null);
    setLoading(true);
    try {
      const { error: oauthErr } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: window.location.origin },
      });
      if (oauthErr) throw oauthErr;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google sign-in failed.");
      setLoading(false);
    }
  }

  const modalTitle =
    mode === "signin"
      ? "Sign In to MathLab"
      : mode === "signup"
        ? "Create MathLab Account"
        : "Reset Password";

  const submitLabel = loading
    ? mode === "forgot"
      ? "Sending..."
      : "Submitting..."
    : mode === "signin"
      ? "Sign In"
      : mode === "signup"
        ? "Create Account"
        : "Send Reset Link";

  const headerControl = user ? (
    <>
      <div className="flex w-full items-center justify-between gap-2 sm:w-auto sm:justify-start">
        <span className="min-w-0 truncate whitespace-nowrap rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 text-xs text-[var(--text-secondary)] sm:max-w-[180px]">
          {user.email ?? user.id}
        </span>
        <button
          type="button"
          onClick={() => setConfirmSignOutOpen(true)}
          className="shrink-0 whitespace-nowrap rounded border border-rose-500/30 bg-rose-500/5 px-3 py-1.5 text-xs font-medium text-[var(--status-error)] transition hover:border-rose-500/50 hover:bg-rose-500/10"
        >
          Sign Out
        </button>
      </div>

      <Modal
        open={confirmSignOutOpen}
        onClose={() => {
          if (!loading) setConfirmSignOutOpen(false);
        }}
        maxWidthClass="max-w-xs"
      >
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">
          Sign Out of MathLab?
        </h2>
        <p className="mt-1.5 text-xs text-[var(--text-secondary)]">
          You are signed in as{" "}
          <span className="font-medium text-[var(--text-primary)]">
            {user.email ?? user.id}
          </span>
          . Any unsaved edits in the current cell should be saved before signing out.
        </p>

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setConfirmSignOutOpen(false)}
            disabled={loading}
            className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSignOut()}
            disabled={loading}
            className="rounded bg-[var(--accent-ink)] px-3 py-1.5 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90 disabled:opacity-60"
          >
            {loading ? "Signing out..." : "Sign Out"}
          </button>
        </div>
      </Modal>
    </>
  ) : (
    <>
      <div className="flex w-full items-center justify-between gap-2 sm:w-auto sm:justify-start">
        <span className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-1.5 text-xs text-[var(--text-muted)]">
          Guest
        </span>
        <button
          type="button"
          onClick={() => {
            switchMode("signin");
            setOpen(true);
          }}
          className="shrink-0 whitespace-nowrap rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
        >
          Sign In
        </button>
      </div>

      <Modal
        open={open}
        onClose={() => {
          if (!loading) setOpen(false);
        }}
        maxWidthClass="max-w-sm"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">{modalTitle}</h2>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            Close
          </button>
        </div>

        {mode === "forgot" && (
          <p className="mt-2 text-xs text-[var(--text-secondary)]">
            Enter your account email and we&apos;ll send you a password reset link.
          </p>
        )}

        <form onSubmit={handleSubmit} noValidate className="mt-4 space-y-3">
          <div>
            <label className="mb-1 block text-xs text-[var(--text-secondary)]">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) setEmailError(null);
              }}
              aria-invalid={Boolean(emailError)}
              className={`w-full rounded border bg-[var(--bg-subtle)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none ${
                emailError
                  ? "border-rose-500/60 focus:border-rose-500"
                  : "border-[var(--border-hairline)] focus:border-[var(--border-strong)]"
              }`}
            />
            <ErrorCard message={emailError} className="mt-2" />
          </div>

          {mode !== "forgot" && (
            <PasswordInput
              label="Password"
              value={password}
              onChange={setPassword}
              labelAction={
                mode === "signin" ? (
                  <button
                    type="button"
                    onClick={() => switchMode("forgot")}
                    className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:underline"
                  >
                    Forgot password?
                  </button>
                ) : null
              }
            />
          )}

          <ErrorCard message={error} />
          {message && (
            <div className="rounded border border-emerald-500/40 bg-emerald-500/10 p-2 text-xs text-[var(--status-verified)]">
              {message}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-[var(--accent-ink)] py-2 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90 disabled:opacity-60"
          >
            {submitLabel}
          </button>
        </form>

        <div className="mt-3 text-center text-xs text-[var(--text-secondary)]">
          {mode === "signin" ? (
            <>
              No account yet?{" "}
              <button
                type="button"
                onClick={() => switchMode("signup")}
                className="font-medium text-[var(--text-primary)] underline"
              >
                Sign Up
              </button>
            </>
          ) : mode === "signup" ? (
            <>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => switchMode("signin")}
                className="font-medium text-[var(--text-primary)] underline"
              >
                Sign In
              </button>
            </>
          ) : (
            <>
              Remembered your password?{" "}
              <button
                type="button"
                onClick={() => switchMode("signin")}
                className="font-medium text-[var(--text-primary)] underline"
              >
                Back to Sign In
              </button>
            </>
          )}
        </div>

        {mode !== "forgot" && (
          <>
            <div className="my-3 flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
              <div className="h-px flex-1 bg-[var(--border-hairline)]" />
              <span>or</span>
              <div className="h-px flex-1 bg-[var(--border-hairline)]" />
            </div>

            <div className="space-y-2">
              <button
                type="button"
                onClick={() => void handleGoogleSignIn()}
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] py-2 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] disabled:opacity-60"
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24Z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14Z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96Z"
                  />
                </svg>
                Continue with Google
              </button>

              <button
                type="button"
                onClick={() => setOpen(false)}
                className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                Continue as Guest
              </button>
            </div>
          </>
        )}
      </Modal>
    </>
  );

  return (
    <>
      {headerControl}

      <Modal
        open={recoveryOpen}
        onClose={() => {
          if (!recoveryLoading) {
            setRecoveryError(null);
            onCloseRecovery?.();
          }
        }}
        maxWidthClass="max-w-sm"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            Set New Password
          </h2>
          <button
            type="button"
            disabled={recoveryLoading}
            onClick={() => {
              setRecoveryError(null);
              onCloseRecovery?.();
            }}
            className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            Close
          </button>
        </div>

        <p className="mt-2 text-xs text-[var(--text-secondary)]">
          Enter a new password for your MathLab account.
        </p>

        <form onSubmit={handlePasswordUpdate} noValidate className="mt-4 space-y-3">
          <PasswordInput
            label="New Password"
            value={newPassword}
            onChange={setNewPassword}
          />
          <PasswordInput
            label="Confirm New Password"
            value={confirmNewPassword}
            onChange={setConfirmNewPassword}
          />

          <ErrorCard message={recoveryError} />

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              disabled={recoveryLoading}
              onClick={() => {
                setRecoveryError(null);
                onCloseRecovery?.();
              }}
              className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={recoveryLoading}
              className="rounded bg-[var(--accent-ink)] px-3 py-1.5 text-xs font-semibold text-[var(--accent-ink-fg)] hover:opacity-90 disabled:opacity-60"
            >
              {recoveryLoading ? "Updating..." : "Update Password"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
