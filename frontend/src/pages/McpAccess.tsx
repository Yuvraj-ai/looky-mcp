import { useCallback, useEffect, useState } from "react";
import {
  generateMcpKey,
  getConfigSnippets,
  getMcpCredentialStatus,
  revokeMcpKey,
  type ConfigSnippets,
  type McpCredentialStatus,
} from "../api/mcpCredential";

type ClientTab = "opencode" | "claude_cli" | "claude_json" | "codex";

export default function McpAccess() {
  const [status, setStatus] = useState<McpCredentialStatus | null>(null);
  const [freshKey, setFreshKey] = useState<string | null>(null);
  const [snippets, setSnippets] = useState<ConfigSnippets | null>(null);
  const [activeTab, setActiveTab] = useState<ClientTab>("opencode");
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, sn] = await Promise.all([
        getMcpCredentialStatus(),
        getConfigSnippets().catch(() => null),
      ]);
      setStatus(s);
      setSnippets(sn);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function copyToClipboard(text: string, fieldId: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldId);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      // Fallback if clipboard API is restricted
      setError("Failed to copy to clipboard");
    }
  }

  async function handleGenerate() {
    if (
      status?.configured &&
      !window.confirm(
        "Regenerating your key will immediately invalidate your active key. Any connected coding agents must be updated with the new key. Continue?"
      )
    ) {
      return;
    }

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
    if (
      !window.confirm(
        "Are you sure you want to revoke MCP access? Connected coding agents will lose access immediately until you generate a new key."
      )
    ) {
      return;
    }

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

  let currentSnippet = "";
  let snippetDescription = "";

  if (snippets) {
    if (activeTab === "opencode") {
      currentSnippet = snippets.opencode;
      snippetDescription =
        "Add this to opencode.json. Set the VISION_MCP_KEY environment variable to your MCP key.";
    } else if (activeTab === "claude_cli") {
      currentSnippet = snippets.claude_code_cli;
      snippetDescription =
        "Run this command in your terminal to connect Claude Code to Vision MCP.";
    } else if (activeTab === "claude_json") {
      currentSnippet = snippets.claude_code_json;
      snippetDescription =
        "Add this to your project .mcp.json or global ~/.claude.json configuration file.";
    } else if (activeTab === "codex") {
      currentSnippet = snippets.codex_toml;
      snippetDescription =
        "Add this to your ~/.codex/config.toml configuration file.";
    }
  }

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
          <div style={{ marginBottom: "1rem" }}>
            <p className="notice" style={{ color: "#d97706" }}>
              ⚠️ Copy this key now — it will not be shown again. Put it in an
              environment variable (e.g. <code>VISION_MCP_KEY</code>) and never
              commit it to a public repository.
            </p>
            <div className="code-container">
              <button
                type="button"
                className="copy-button"
                onClick={() => void copyToClipboard(freshKey, "key")}
              >
                {copiedField === "key" ? "Copied!" : "Copy Key"}
              </button>
              <div className="mono">{freshKey}</div>
            </div>
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

      {snippets && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h2>Agent Configuration Snippets</h2>
          <div className="tab-group">
            <button
              type="button"
              className={`tab-btn ${activeTab === "opencode" ? "active" : ""}`}
              onClick={() => setActiveTab("opencode")}
            >
              OpenCode (opencode.json)
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === "claude_cli" ? "active" : ""}`}
              onClick={() => setActiveTab("claude_cli")}
            >
              Claude Code (CLI)
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === "claude_json" ? "active" : ""}`}
              onClick={() => setActiveTab("claude_json")}
            >
              Claude Code (.mcp.json)
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === "codex" ? "active" : ""}`}
              onClick={() => setActiveTab("codex")}
            >
              Codex (config.toml)
            </button>
          </div>

          <p className="notice">{snippetDescription}</p>

          <div className="code-container">
            <button
              type="button"
              className="copy-button"
              onClick={() => void copyToClipboard(currentSnippet, "snippet")}
            >
              {copiedField === "snippet" ? "Copied!" : "Copy Snippet"}
            </button>
            <div className="mono">{currentSnippet}</div>
          </div>
        </div>
      )}
    </section>
  );
}
