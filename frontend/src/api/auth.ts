import { api } from "./client";

export interface User {
  id: string;
  email: string;
}

export async function login(email: string, password: string): Promise<User> {
  return api.post<User>("/auth/login", { email, password });
}

export async function logout(): Promise<void> {
  return api.post<void>("/auth/logout");
}

export async function me(): Promise<User> {
  return api.get<User>("/auth/me");
}
