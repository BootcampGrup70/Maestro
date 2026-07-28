export type WSEventType =
  | "agent_status"
  | "agent_snapshot"
  | "run_started"
  | "run_finished"
  | "message_created"
  | "message_delta"
  | "thinking_delta"
  | "tool_call_created"
  | "tool_call_updated"
  | "error";

export interface WSEvent<T = Record<string, unknown>> {
  type: WSEventType;
  agent_id: string | null;
  data: T;
  ts: number;
}
