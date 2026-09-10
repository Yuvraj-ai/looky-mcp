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
