import { create } from "zustand";
import { agentsApi } from "../api/agents";
import { runsApi } from "../api/runs";
import { messagesApi } from "../api/messages";
import type { Agent, AgentCreateInput, AgentStatus, Run, Message } from "../api/types";

interface StreamingState {
  runId: string;
  content: string;
  thinking: string;
}

export interface ToolCallState {
  id: string;
  operation: string;
  status: string;
}

interface AppState {
  agents: Agent[];
  agentsLoading: boolean;
  agentsError: string | null;
  fetchAgents: () => Promise<void>;
  createAgent: (data: AgentCreateInput) => Promise<Agent>;
  updateAgentPosition: (id: string, x: number, y: number) => Promise<void>;
  removeAgent: (id: string) => Promise<void>;
  patchAgentLocal: (id: string, patch: Partial<Agent>) => void;
  refreshAgent: (id: string) => Promise<void>;
  applyAgentSnapshot: (
    snapshot: { agent_id: string; status: string; error_message: string | null }[]
  ) => void;

  selectedAgentId: string | null;
  selectAgent: (id: string | null) => void;

  runsByAgent: Record<string, Run[]>;
  fetchRuns: (agentId: string) => Promise<void>;
  startRun: (agentId: string, prompt: string) => Promise<Run>;

  messagesByAgent: Record<string, Message[]>;
  fetchMessages: (agentId: string) => Promise<void>;
  appendMessageLocal: (agentId: string, message: Message) => void;

  streamingByAgent: Record<string, StreamingState | undefined>;
  startStreaming: (agentId: string, runId: string) => void;
  appendStreamDelta: (agentId: string, kind: "content" | "thinking", delta: string) => void;
  clearStreaming: (agentId: string) => void;

  toolCallsByAgent: Record<string, ToolCallState[]>;
  upsertToolCall: (agentId: string, id: string, operation: string) => void;
  updateToolCallStatus: (agentId: string, id: string, status: string) => void;
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

  refreshAgent: async (id) => {
    const agent = await agentsApi.get(id);
    set((state) => ({ agents: state.agents.map((a) => (a.id === id ? agent : a)) }));
  },

  applyAgentSnapshot: (snapshot) => {
    set((state) => ({
      agents: state.agents.map((a) => {
        const found = snapshot.find((x) => x.agent_id === a.id);
        return found
          ? { ...a, status: found.status as AgentStatus, error_message: found.error_message }
          : a;
      }),
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
        [agentId]: [run, ...(state.runsByAgent[agentId] ?? [])],
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

  streamingByAgent: {},
  startStreaming: (agentId, runId) => {
    set((state) => ({
      streamingByAgent: {
        ...state.streamingByAgent,
        [agentId]: { runId, content: "", thinking: "" },
      },
    }));
  },
  appendStreamDelta: (agentId, kind, delta) => {
    set((state) => {
      const current = state.streamingByAgent[agentId];
      if (!current) return {};
      return {
        streamingByAgent: {
          ...state.streamingByAgent,
          [agentId]: { ...current, [kind]: current[kind] + delta },
        },
      };
    });
  },
  clearStreaming: (agentId) => {
    set((state) => {
      const next = { ...state.streamingByAgent };
      delete next[agentId];
      return { streamingByAgent: next };
    });
  },

  toolCallsByAgent: {},
  upsertToolCall: (agentId, id, operation) => {
    set((state) => ({
      toolCallsByAgent: {
        ...state.toolCallsByAgent,
        [agentId]: [...(state.toolCallsByAgent[agentId] ?? []), { id, operation, status: "pending" }],
      },
    }));
  },
  updateToolCallStatus: (agentId, id, status) => {
    set((state) => ({
      toolCallsByAgent: {
        ...state.toolCallsByAgent,
        [agentId]: (state.toolCallsByAgent[agentId] ?? []).map((tc) =>
          tc.id === id ? { ...tc, status } : tc
        ),
      },
    }));
  },
}));
