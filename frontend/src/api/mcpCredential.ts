import { api } from "./client";

export interface McpCredentialStatus {
  configured: boolean;
  created_at: string | null;
}

export interface McpCredentialGenerated {
  key: string;
}

export const getMcpCredentialStatus = () =>
  api.get<McpCredentialStatus>("/mcp-credential");

export const generateMcpKey = () =>
  api.post<McpCredentialGenerated>("/mcp-credential/generate");

export const revokeMcpKey = () => api.post<void>("/mcp-credential/revoke");

export interface OpenCodeSnippet {
  snippet: string;
}

export const getOpenCodeSnippet = () =>
  api.get<OpenCodeSnippet>("/mcp-credential/opencode-snippet");

export interface ConfigSnippets {
  opencode: string;
  claude_code_cli: string;
  claude_code_json: string;
  codex_toml: string;
}

export const getConfigSnippets = () =>
  api.get<ConfigSnippets>("/mcp-credential/config-snippets");

