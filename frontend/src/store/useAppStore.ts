import { create } from "zustand";
import { agentsApi } from "../api/agents";
import { runsApi } from "../api/runs";
import { messagesApi } from "../api/messages";
import { toolCallsApi } from "../api/toolCalls";
import { libraryApi } from "../api/library";
import type {
  Agent,
  AgentCreateInput,
  Run,
  Message,
  ToolCall,
  LibraryWorkflow,
  WorkflowPublishInput,
  WorkflowImportInput,
  WorkflowImportResult,
} from "../api/types";

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
  updateAgentStatus: (id: string, status: string, errorMessage?: string) => void;
  setAgentsSnapshot: (agents: Record<string, unknown>[]) => void;

  selectedAgentId: string | null;
  selectAgent: (id: string | null) => void;

  runsByAgent: Record<string, Run[]>;
  activeRunByAgent: Record<string, string>;
  fetchRuns: (agentId: string) => Promise<void>;
  startRun: (agentId: string, prompt: string) => Promise<Run>;
  setActiveRun: (agentId: string, runId: string) => void;
  clearActiveRun: (agentId: string) => void;

  messagesByAgent: Record<string, Message[]>;
  fetchMessages: (agentId: string) => Promise<void>;
  appendMessageLocal: (agentId: string, message: Message) => void;
  appendMessageDelta: (agentId: string, delta: string) => void;

  toolCallsByAgent: Record<string, ToolCall[]>;
  fetchToolCalls: (agentId: string) => Promise<void>;
  addToolCall: (agentId: string, toolCall: Record<string, unknown>) => void;
  updateToolCall: (agentId: string, toolCall: Record<string, unknown>) => void;

  libraryWorkflows: LibraryWorkflow[];
  libraryLoading: boolean;
  libraryError: string | null;
  fetchLibraryWorkflows: (params?: { tag?: string; search?: string }) => Promise<void>;
  publishWorkflow: (data: WorkflowPublishInput) => Promise<LibraryWorkflow>;
  deleteLibraryWorkflow: (id: string) => Promise<void>;
  importWorkflow: (id: string, data?: WorkflowImportInput) => Promise<WorkflowImportResult>;
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
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? agent : a)),
    }));
  },

updateAgentStatus: (id, status, errorMessage) => {
  set((state) => ({
    agents: state.agents.map((a) =>
      a.id === id
        ? { ...a, status: status as Agent["status"], error_message: errorMessage ?? null }
        : a
    ),
  }));
},

  setAgentsSnapshot: (agentSnapshots) => {
    set((state) => {
      const updated = [...state.agents];
      for (const snap of agentSnapshots) {
        const idx = updated.findIndex((a) => a.id === snap.id);
        if (idx !== -1) {
          updated[idx] = { ...updated[idx], ...(snap as Partial<Agent>) };
        }
      }
      return { agents: updated };
    });
  },

  selectedAgentId: null,
  selectAgent: (id) => set({ selectedAgentId: id }),

  runsByAgent: {},
  activeRunByAgent: {},

  fetchRuns: async (agentId) => {
    const runs = await runsApi.list(agentId);
    set((state) => ({
      runsByAgent: { ...state.runsByAgent, [agentId]: runs },
    }));
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

  setActiveRun: (agentId, runId) => {
    set((state) => ({
      activeRunByAgent: { ...state.activeRunByAgent, [agentId]: runId },
    }));
  },

  clearActiveRun: (agentId) => {
    set((state) => {
      const updated = { ...state.activeRunByAgent };
      delete updated[agentId];
      return { activeRunByAgent: updated };
    });
  },

  messagesByAgent: {},

  fetchMessages: async (agentId) => {
    const messages = await messagesApi.list(agentId);
    set((state) => ({
      messagesByAgent: { ...state.messagesByAgent, [agentId]: messages },
    }));
  },

  appendMessageLocal: (agentId, message) => {
    set((state) => ({
      messagesByAgent: {
        ...state.messagesByAgent,
        [agentId]: [...(state.messagesByAgent[agentId] ?? []), message],
      },
    }));
  },

  appendMessageDelta: (agentId, delta) => {
    set((state) => {
      const messages = state.messagesByAgent[agentId] ?? [];
      if (messages.length === 0) return {};
      const last = messages[messages.length - 1];
      const updated = {
        ...last,
        content: (last.content ?? "") + delta,
      };
      return {
        messagesByAgent: {
          ...state.messagesByAgent,
          [agentId]: [...messages.slice(0, -1), updated],
        },
      };
    });
  },

  toolCallsByAgent: {},

  fetchToolCalls: async (agentId) => {
    const toolCalls = await toolCallsApi.list(agentId);
    set((state) => ({
      toolCallsByAgent: { ...state.toolCallsByAgent, [agentId]: toolCalls },
    }));
  },

  // WS payloads only carry a partial shape ({tool_call_id, operation}/{tool_call_id, status}),
  // not a full ToolCall row - refetch from the REST endpoint rather than merging by id.
  addToolCall: (agentId) => {
    void useAppStore.getState().fetchToolCalls(agentId);
  },

  updateToolCall: (agentId) => {
    void useAppStore.getState().fetchToolCalls(agentId);
  },

  libraryWorkflows: [],
  libraryLoading: false,
  libraryError: null,

  fetchLibraryWorkflows: async (params) => {
    set({ libraryLoading: true, libraryError: null });
    try {
      const libraryWorkflows = await libraryApi.list(params);
      set({ libraryWorkflows, libraryLoading: false });
    } catch (err) {
      set({ libraryError: (err as Error).message, libraryLoading: false });
    }
  },

  publishWorkflow: async (data) => {
    const workflow = await libraryApi.publish(data);
    set((state) => ({ libraryWorkflows: [workflow, ...state.libraryWorkflows] }));
    return workflow;
  },

  deleteLibraryWorkflow: async (id) => {
    await libraryApi.delete(id);
    set((state) => ({
      libraryWorkflows: state.libraryWorkflows.filter((w) => w.id !== id),
    }));
  },

  importWorkflow: async (id, data) => {
    const result = await libraryApi.import(id, data);
    await useAppStore.getState().fetchAgents();
    return result;
  },
}));