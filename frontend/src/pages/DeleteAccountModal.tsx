import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";

interface DeleteAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DeleteAccountModal({
  isOpen,
  onClose,
}: DeleteAccountModalProps) {
  const { user, deleteAccount } = useAuth();
  const [confirmEmail, setConfirmEmail] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const userEmail = user?.email ?? "";
  const isMatch =
    confirmEmail.trim().toLowerCase() === userEmail.trim().toLowerCase() &&
    userEmail.length > 0;
  const canDelete = isMatch && agreed && !busy;

  // Reset state whenever modal is opened
  useEffect(() => {
    if (isOpen) {
      setConfirmEmail("");
      setAgreed(false);
      setError(null);
      setBusy(false);
    }
  }, [isOpen]);

  // Handle ESC key to close
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && isOpen && !busy) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, busy, onClose]);

  if (!isOpen) return null;

  async function handleDelete(e: React.FormEvent) {
    e.preventDefault();
    if (!canDelete) return;

    setBusy(true);
    setError(null);
    try {
      await deleteAccount(confirmEmail.trim());
      window.location.href = "/login?deleted=true";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete account");
      setBusy(false);
    }
  }

  return (
    <div
      className="delete-modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-account-title"
    >
      <div className="delete-modal-card">
        {/* Header */}
        <div className="delete-modal-header">
          <div className="delete-danger-badge">
            <span className="danger-icon">⚠️</span>
            <span>DANGER ZONE — IRREVERSIBLE ACTION</span>
          </div>
          <button
            type="button"
            className="delete-modal-close-btn"
            onClick={onClose}
            disabled={busy}
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>

        <h3 id="delete-account-title" className="delete-modal-title">
          Delete Account &amp; Erase All Data
        </h3>

        {/* Warning Callout */}
        <div className="delete-warning-box">
          <p className="delete-warning-intro">
            This action <strong>cannot be undone</strong>. Deleting your account
            will immediately and permanently erase all data associated with{" "}
            <span className="user-email-highlight">{userEmail}</span>:
          </p>
          <ul className="delete-impact-list">
            <li>
              <span className="impact-bullet">🗑️</span>
              <div>
                <strong>Vision Profiles:</strong> All your custom vision
                endpoints and encrypted model API keys will be wiped
                permanently.
              </div>
            </li>
            <li>
              <span className="impact-bullet">🗑️</span>
              <div>
                <strong>System Prompts:</strong> All custom system prompts you
                created will be deleted.
              </div>
            </li>
            <li>
              <span className="impact-bullet">🗑️</span>
              <div>
                <strong>MCP Gateway Access:</strong> Your active MCP key will be
                immediately revoked. Any connected agents (Claude Code,
                OpenCode, Codex) will lose access.
              </div>
            </li>
            <li>
              <span className="impact-bullet">🔒</span>
              <div>
                <strong>Session Revocation:</strong> Your current session will
                be terminated and you will be returned to the login screen.
              </div>
            </li>
          </ul>
        </div>

        {/* Confirmation Form */}
        <form onSubmit={handleDelete} className="delete-form">
          <div className="delete-confirm-group">
            <label htmlFor="confirm-email-input" className="confirm-email-label">
              <span>To confirm, please enter or paste your exact email address:</span>
              <div className="target-email-display">
                <code className="target-email-code">{userEmail}</code>
              </div>
            </label>
            <input
              id="confirm-email-input"
              type="email"
              className={`confirm-email-input ${
                confirmEmail.length > 0
                  ? isMatch
                    ? "input-match"
                    : "input-mismatch"
                  : ""
              }`}
              placeholder={userEmail}
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              disabled={busy}
              autoComplete="off"
              required
            />
            {confirmEmail.length > 0 && !isMatch && (
              <span className="mismatch-hint">
                Email address does not match. Please verify and try again.
              </span>
            )}
          </div>

          <label className="delete-checkbox-label">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              disabled={busy}
            />
            <span>
              I understand that this action is irreversible and all my data will
              be permanently erased.
            </span>
          </label>

          {error && <p className="error delete-error">{error}</p>}

          <div className="delete-modal-actions">
            <button
              type="button"
              className="btn-cancel"
              onClick={onClose}
              disabled={busy}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-danger-delete"
              disabled={!canDelete}
            >
              {busy ? "Deleting account..." : "Permanently Delete My Account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
