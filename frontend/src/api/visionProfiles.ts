import { api } from "./client";
import { listSystemPrompts, type SystemPrompt } from "./systemPrompts";

export interface VisionProfile {
  id: string;
  name: string;
  endpoint: string;
  model: string;
  system_prompt_id: string;
  has_api_key: boolean;
  is_active: boolean;
}

export interface VisionProfileInput {
  name: string;
  endpoint: string;
  model: string;
  api_key: string;
  system_prompt_id: string;
}

export const listVisionProfiles = () =>
  api.get<VisionProfile[]>("/vision-profiles");

export const createVisionProfile = (body: VisionProfileInput) =>
  api.post<VisionProfile>("/vision-profiles", body);

export const updateVisionProfile = (id: string, body: VisionProfileInput) =>
  api.put<VisionProfile>(`/vision-profiles/${id}`, body);

export const deleteVisionProfile = (id: string) =>
  api.delete<void>(`/vision-profiles/${id}`);

export const activateVisionProfile = (id: string) =>
  api.post<VisionProfile>(`/vision-profiles/${id}/activate`);

export const loadProfileOptions = (): Promise<SystemPrompt[]> =>
  listSystemPrompts();
