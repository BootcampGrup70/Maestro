import { create } from "zustand";
import { agentsApi } from "../api/agents";
import { runsApi } from "../api/runs";
import { messagesApi } from "../api/messages";
import type { Agent, AgentCreateInput, Run, Message } from "../api/types";

interface AppState {
  agents: Agent[];
  agentsLoading: boolean;
  agentsError: string | null;
  fetchAgents: () => Promise<void>;
  createAgent: (data: AgentCreateInput) => Promise<Agent>;
  updateAgentPosition: (id: string, x: number, y: number) => Promise<void>;
  removeAgent: (id: string) => Promise<void>;
  patchAgentLocal: (id: string, patch: Partial<Agent>) => void;

  selectedAgentId: string | null;
  selectAgent: (id: string | null) => void;

  runsByAgent: Record<string, Run[]>;
  fetchRuns: (agentId: string) => Promise<void>;
  startRun: (agentId: string, prompt: string) => Promise<Run>;

  messagesByAgent: Record<string, Message[]>;
  fetchMessages: (agentId: string) => Promise<void>;
  appendMessageLocal: (agentId: string, message: Message) => void;
}

export const useAppStore = create<AppState>((set) => ({
  agents: [],
  agentsLoading: false,
  agentsError: null,

  fetchAgents: async () => {
    set({ agentsLoading: true, agentsError: null });
    try {
      const agents = await agentsApi.list();
      set({ agents, agentsLoading: false });
    } catch (err) {
      set({ agentsError: (err as Error).message, agentsLoading: false });
    }
  },

  createAgent: async (data) => {
    const agent = await agentsApi.create(data);
    set((state) => ({ agents: [...state.agents, agent] }));
    return agent;
  },

  updateAgentPosition: async (id, x, y) => {
    const updated = await agentsApi.updatePosition(id, x, y);
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? updated : a)),
    }));
  },

  removeAgent: async (id) => {
    await agentsApi.delete(id);
    set((state) => ({ agents: state.agents.filter((a) => a.id !== id) }));
  },

  patchAgentLocal: (id, patch) => {
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    }));
  },

  selectedAgentId: null,
  selectAgent: (id) => set({ selectedAgentId: id }),

  runsByAgent: {},
  fetchRuns: async (agentId) => {
    const runs = await runsApi.list(agentId);
    set((state) => ({ runsByAgent: { ...state.runsByAgent, [agentId]: runs } }));
  },
  startRun: async (agentId, prompt) => {
    const run = await runsApi.start(agentId, prompt);
    set((state) => ({
      runsByAgent: {
        ...state.runsByAgent,
        [agentId]: [...(state.runsByAgent[agentId] ?? []), run],
      },
    }));
    return run;
  },

  messagesByAgent: {},
  fetchMessages: async (agentId) => {
    const messages = await messagesApi.list(agentId);
    set((state) => ({ messagesByAgent: { ...state.messagesByAgent, [agentId]: messages } }));
  },
  appendMessageLocal: (agentId, message) => {
    set((state) => ({
      messagesByAgent: {
        ...state.messagesByAgent,
        [agentId]: [...(state.messagesByAgent[agentId] ?? []), message],
      },
    }));
  },
}));
