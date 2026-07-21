import { api } from "./client";
import type { Message } from "./types";

export const messagesApi = {
  list: (agentId: string) => api.get<Message[]>(`/agents/${agentId}/messages`),
};
