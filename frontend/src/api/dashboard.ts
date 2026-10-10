import { api } from "./client";

export interface DashboardResponse {
  setup: {
    active_profile_name: string | null;
    active_model: string | null;
    profile_count: number;
    prompt_count: number;
    mcp_configured: boolean;
  };
  activity: {
    total_7d: number;
    succeeded_7d: number;
    failed_7d: number;
    average_duration_ms: number | null;
    daily: {
      date: string;
      total: number;
      succeeded: number;
      failed: number;
      average_duration_ms: number | null;
    }[];
    recent: {
      id: string;
      created_at: string;
      mode: string;
      profile_name: string | null;
      model: string | null;
      duration_ms: number;
      succeeded: boolean;
      error_code: string | null;
    }[];
  };
}

export const getDashboard = () => api.get<DashboardResponse>("/dashboard");
