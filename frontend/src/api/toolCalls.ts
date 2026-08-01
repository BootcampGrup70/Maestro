import { api } from "./client";
import type { ToolCall } from "./types";

export const toolCallsApi = {
  list: (agentId: string) => api.get<ToolCall[]>(`/agents/${agentId}/tool-calls`),
};
