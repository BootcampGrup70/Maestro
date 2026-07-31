import { useEffect, useRef, useCallback } from "react";
import { useAppStore } from "../store/useAppStore";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws";

type WSEvent = {
  type: string;
  agent_id?: string;
  run_id?: string;
  data?: Record<string, unknown>;
};

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const store = useAppStore();

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      const msg: WSEvent = JSON.parse(event.data);

      switch (msg.type) {
        case "agent_status":
          if (msg.agent_id && msg.data?.status) {
            store.updateAgentStatus(
              msg.agent_id,
              msg.data.status as string,
              msg.data.error_message as string | undefined
            );
          }
          break;

        case "message_delta":
          if (msg.agent_id && msg.data?.content) {
            store.appendMessageDelta(
              msg.agent_id,
              msg.data.content as string
            );
          }
          break;

        case "tool_call_created":
          if (msg.agent_id && msg.data) {
            store.addToolCall(msg.agent_id, msg.data);
          }
          break;

        case "tool_call_updated":
          if (msg.agent_id && msg.data) {
            store.updateToolCall(msg.agent_id, msg.data);
          }
          break;

        case "run_started":
          if (msg.agent_id && msg.run_id) {
            store.setActiveRun(msg.agent_id, msg.run_id);
          }
          break;

        case "run_finished":
          if (msg.agent_id) {
            store.clearActiveRun(msg.agent_id);
          }
          break;

        case "agent_deleted":
          if (msg.agent_id) {
            store.removeAgent(msg.agent_id);
          }
          break;

        case "snapshot":
          if (msg.data?.agents) {
            store.setAgentsSnapshot(
              msg.data.agents as Record<string, unknown>[]
            );
          }
          break;

        default:
          break;
      }
    },
    [store]
  );

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      console.log("WebSocket bağlandı");
    };

    socket.onmessage = handleMessage;

    socket.onclose = () => {
      console.log("WebSocket bağlantısı kapandı");
    };

    socket.onerror = (err) => {
      console.error("WebSocket hatası:", err);
    };

    return () => {
      socket.close();
    };
  }, [handleMessage]);

  const send = useCallback((data: unknown) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}