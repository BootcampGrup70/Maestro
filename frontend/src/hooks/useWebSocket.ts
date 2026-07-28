import { useEffect, useRef } from "react";
import { useAppStore } from "../store/useAppStore";
import type { Agent } from "../api/types";
import type { WSEvent } from "../api/ws";

function resolveWsUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
  const wsBase = base.replace(/^http/, "ws").replace(/\/api\/?$/, "");
  return `${wsBase}/ws`;
}

export function useWebSocket() {
  const patchAgentLocal = useAppStore((s) => s.patchAgentLocal);
  const applyAgentSnapshot = useAppStore((s) => s.applyAgentSnapshot);
  const startStreaming = useAppStore((s) => s.startStreaming);
  const appendStreamDelta = useAppStore((s) => s.appendStreamDelta);
  const clearStreaming = useAppStore((s) => s.clearStreaming);
  const fetchMessages = useAppStore((s) => s.fetchMessages);
  const upsertToolCall = useAppStore((s) => s.upsertToolCall);
  const updateToolCallStatus = useAppStore((s) => s.updateToolCallStatus);

  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      const ws = new WebSocket(resolveWsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
      };

      ws.onmessage = (event) => {
        let parsed: WSEvent;
        try {
          parsed = JSON.parse(event.data);
        } catch {
          return;
        }
        const { type, agent_id, data } = parsed;

        switch (type) {
          case "agent_snapshot":
            applyAgentSnapshot(
              data.agents as { agent_id: string; status: string; error_message: string | null }[]
            );
            break;
          case "agent_status":
            if (agent_id) {
              patchAgentLocal(agent_id, {
                status: data.status as Agent["status"],
                error_message: (data.error_message as string) ?? null,
              });
            }
            break;
          case "run_started":
            if (agent_id) startStreaming(agent_id, data.run_id as string);
            break;
          case "message_delta":
            if (agent_id) appendStreamDelta(agent_id, "content", data.delta as string);
            break;
          case "thinking_delta":
            if (agent_id) appendStreamDelta(agent_id, "thinking", data.delta as string);
            break;
          case "message_created":
            if (agent_id) {
              fetchMessages(agent_id);
              clearStreaming(agent_id);
            }
            break;
          case "tool_call_created":
            if (agent_id) upsertToolCall(agent_id, data.tool_call_id as string, data.operation as string);
            break;
          case "tool_call_updated":
            if (agent_id) updateToolCallStatus(agent_id, data.tool_call_id as string, data.status as string);
            break;
          case "run_finished":
            if (agent_id) clearStreaming(agent_id);
            break;
          case "error":
            console.error("WS error event:", data);
            break;
        }
      };

      ws.onclose = () => {
        if (cancelled) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 10000);
        retryRef.current += 1;
        setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, []);
}
