import { useEffect, useState } from "react";
import {
  getExtraInstructions,
  putExtraInstructions,
} from "../api/extraInstructions";

export default function ExtraInstructionsCard() {
  const [content, setContent] = useState("");
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    getExtraInstructions()
      .then((r) => setContent(r.content))
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load"),
      );
  }, []);

  async function handleSave() {
    setBusy(true);
    setError(null);
    try {
      await putExtraInstructions(content);
      setSaved("Saved.");
      setTimeout(() => setSaved(null), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  const isConfigured = content.trim().length > 0;

  return (
    <div
      className={`card extra-instructions-tab ${isExpanded ? "expanded" : ""}`}
    >
      <button
        type="button"
        className="extra-instructions-toggle"
        onClick={() => setIsExpanded((prev) => !prev)}
        aria-expanded={isExpanded}
        aria-label="Toggle Universal Extra Instructions"
      >
        <div className="extra-instructions-header-left">
          <span className="extra-instructions-title">
            Universal Extra Instructions
          </span>
          <span
            className={`status-pill ${
              isConfigured ? "status-pill-active" : "status-pill-muted"
            }`}
          >
            {isConfigured ? "Configured" : "Not configured"}
          </span>
        </div>
        <div className="extra-instructions-header-right">
          <span className="expand-label">
            {isExpanded ? "Collapse" : "Expand"}
          </span>
          <svg
            className={`chevron-icon ${isExpanded ? "open" : ""}`}
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </button>

      {isExpanded && (
        <div className="extra-instructions-content">
          <p className="notice" style={{ margin: "0.5rem 0 0.85rem" }}>
            One global prompt appended to every image-description request (never
            used for OCR). Leave empty to disable.
          </p>
          <textarea
            rows={6}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="e.g. Always answer concisely and factually."
          />
          {error && <p className="error">{error}</p>}
          <div className="actions" style={{ marginTop: "0.75rem" }}>
            <button
              className="btn-primary"
              onClick={() => void handleSave()}
              disabled={busy}
            >
              Save
            </button>
            <button type="button" onClick={() => setIsExpanded(false)}>
              Collapse
            </button>
            {saved && <span className="notice">{saved}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
