import { api } from "./client";
import type { Agent, AgentCreateInput, AgentUpdateInput } from "./types";

export const agentsApi = {
  list: () => api.get<Agent[]>("/agents"),
  get: (id: string) => api.get<Agent>(`/agents/${id}`),
  create: (data: AgentCreateInput) => api.post<Agent>("/agents", data),
  update: (id: string, data: AgentUpdateInput) => api.patch<Agent>(`/agents/${id}`, data),
  updatePosition: (id: string, canvas_x: number, canvas_y: number) =>
    api.patch<Agent>(`/agents/${id}/position`, { canvas_x, canvas_y }),
  delete: (id: string) => api.delete<void>(`/agents/${id}`),

  // PR merge olunca aktif olacak — şimdiden hazır, backend hazır olmadan çağrılırsa 404 döner
  availableModels: () => api.get<string[]>("/agents/available-models"),
};
