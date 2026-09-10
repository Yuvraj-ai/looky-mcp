import { api } from "./client";

export interface SystemPrompt {
  id: string;
  title: string;
  content: string;
}

export const listSystemPrompts = () =>
  api.get<SystemPrompt[]>("/system-prompts");

export const createSystemPrompt = (body: { title: string; content: string }) =>
  api.post<SystemPrompt>("/system-prompts", body);

export const updateSystemPrompt = (
  id: string,
  body: { title: string; content: string },
) => api.put<SystemPrompt>(`/system-prompts/${id}`, body);

export const deleteSystemPrompt = (id: string) =>
  api.delete<void>(`/system-prompts/${id}`);
