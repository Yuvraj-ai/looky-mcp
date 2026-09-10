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

  return (
    <div className="card">
      <h2>Universal Extra Instructions</h2>
      <p className="notice">
        One global prompt appended to every image-description request (never
        used for OCR). Leave empty to disable.
      </p>
      <textarea
        rows={4}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="e.g. Always answer concisely and factually."
      />
      {error && <p className="error">{error}</p>}
      <div className="actions" style={{ marginTop: "0.5rem" }}>
        <button onClick={() => void handleSave()} disabled={busy}>
          Save
        </button>
        {saved && <span className="notice">{saved}</span>}
      </div>
    </div>
  );
}
