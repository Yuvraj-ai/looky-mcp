import { api } from "./client";

export interface ExtraInstructions {
  content: string;
}

export const getExtraInstructions = () =>
  api.get<ExtraInstructions>("/settings/extra-instructions");

export const putExtraInstructions = (content: string) =>
  api.put<ExtraInstructions>("/settings/extra-instructions", { content });
