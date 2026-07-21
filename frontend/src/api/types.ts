// Backend'deki app/models/enums.py ile birebir eşleşir
export type AgentStatus = "idle" | "thinking" | "tool_calling" | "error" | "done" | "queued";
export type RunStatus = "queued" | "running" | "done" | "error";
export type MessageRole = "user" | "assistant" | "system" | "tool";

export interface Agent {
  id: string;
  name: string;
  model: string;
  system_prompt: string | null;
  settings: Record<string, unknown>;
  status: AgentStatus;
  error_message: string | null;
  parent_id: string | null;
  canvas_x: number;
  canvas_y: number;
  created_at: number;
  updated_at: number;
}

export interface AgentCreateInput {
  name: string;
  model: string;
  system_prompt?: string;
  settings?: Record<string, unknown>;
  parent_id?: string;
  canvas_x?: number;
  canvas_y?: number;
}

export interface AgentUpdateInput {
  name?: string;
  model?: string;
  system_prompt?: string;
  settings?: Record<string, unknown>;
  canvas_x?: number;
  canvas_y?: number;
}

export interface Run {
  id: string;
  agent_id: string;
  prompt: string;
  status: RunStatus;
  started_at: number | null;
  finished_at: number | null;
}

export interface Message {
  id: string;
  agent_id: string;
  seq: number;
  role: MessageRole;
  content: string | null;
  thinking: string | null;
  created_at: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  ollama_reachable?: boolean;
}