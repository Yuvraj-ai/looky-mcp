import { useCallback, useEffect, useState } from "react";
import {
  generateMcpKey,
  getMcpCredentialStatus,
  getOpenCodeSnippet,
  revokeMcpKey,
  type McpCredentialStatus,
} from "../api/mcpCredential";

export default function McpAccess() {
  const [status, setStatus] = useState<McpCredentialStatus | null>(null);
  const [freshKey, setFreshKey] = useState<string | null>(null);
  const [snippet, setSnippet] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStatus(await getMcpCredentialStatus());
      setSnippet((await getOpenCodeSnippet()).snippet);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleGenerate() {
    setBusy(true);
    setError(null);
    try {
      const { key } = await generateMcpKey();
      setFreshKey(key);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke() {
    setBusy(true);
    setError(null);
    try {
      await revokeMcpKey();
      setFreshKey(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revoke failed");
    } finally {
      setBusy(false);
    }
  }

  if (status === null) return <div className="loading">Loading...</div>;

  return (
    <section>
      <h1>MCP Access</h1>
      {error && <p className="error">{error}</p>}

      <div className="card">
        <div className="meta">
          <span>
            Status: {status.configured ? "Configured" : "Not configured"}
          </span>
          {status.created_at && (
            <span>Created: {new Date(status.created_at).toLocaleString()}</span>
          )}
        </div>

        {freshKey && (
          <div>
            <p className="notice">
              Copy this key now — it will not be shown again. Put it in an
              environment variable (e.g. <code>VISION_MCP_KEY</code>) and never
              commit it to a repo.
            </p>
            <div className="mono">{freshKey}</div>
          </div>
        )}

        <div className="actions">
          <button onClick={() => void handleGenerate()} disabled={busy}>
            {status.configured ? "Regenerate MCP Key" : "Generate MCP Key"}
          </button>
          {status.configured && (
            <button onClick={() => void handleRevoke()} disabled={busy}>
              Revoke MCP Access
            </button>
          )}
        </div>
      </div>

      {snippet && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h2>OpenCode Configuration</h2>
          <p className="notice">
            Add this to <code>opencode.json</code> and set the{" "}
            <code>VISION_MCP_KEY</code> environment variable to your MCP key.
            The key itself is deliberately not embedded here.
          </p>
          <div className="mono">{snippet}</div>
        </div>
      )}
    </section>
  );
}
