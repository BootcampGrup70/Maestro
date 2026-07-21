import { api } from "./client";
import type { Run } from "./types";

export const runsApi = {
  list: (agentId: string) => api.get<Run[]>(`/agents/${agentId}/runs`),
  start: (agentId: string, prompt: string) =>
    api.post<Run>(`/agents/${agentId}/runs`, { prompt }),
};
