import { useEffect, useRef, useState } from "react";
import { useAppStore } from "../store/useAppStore";
import ChatMessages from "./ChatMessages";
import ChatInput from "./ChatInput";
import ReasoningPanel from "./ReasoningPanel";
import AgentSettingsForm from "./AgentSettingsForm";
import type { Message } from "../api/types";

type Tab = "chat" | "reasoning" | "settings";

interface Props {
  agentId: string;
  onClose: () => void;
}

const POLL_INTERVAL_MS = 1500;
const ACTIVE_STATUSES = new Set(["queued", "thinking", "tool_calling"]);
// Zustand selector'da her render'da yeni [] oluşturmamak için sabit referans.
const EMPTY_MESSAGES: Message[] = [];

export default function AgentDetailPanel({ agentId, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("chat");
  const [isPolling, setIsPolling] = useState(false);

  const agent = useAppStore((s) => s.agents.find((a) => a.id === agentId));
  const messages = useAppStore((s) => s.messagesByAgent[agentId] ?? EMPTY_MESSAGES);
  const fetchMessages = useAppStore((s) => s.fetchMessages);
  const fetchRuns = useAppStore((s) => s.fetchRuns);
  const startRun = useAppStore((s) => s.startRun);
  const refreshAgent = useAppStore((s) => s.refreshAgent);

  const pollTimer = useRef<number | null>(null);

  useEffect(() => {
    fetchMessages(agentId);
    fetchRuns(agentId);
    refreshAgent(agentId);
  }, [agentId]);

  useEffect(() => {
    const shouldPoll = isPolling || (agent && ACTIVE_STATUSES.has(agent.status));

    if (shouldPoll) {
      pollTimer.current = window.setInterval(async () => {
        await Promise.all([fetchMessages(agentId), refreshAgent(agentId)]);
      }, POLL_INTERVAL_MS);
    }

    return () => {
      if (pollTimer.current) {
        window.clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
    };
  }, [isPolling, agent?.status, agentId]);

  useEffect(() => {
    if (agent && !ACTIVE_STATUSES.has(agent.status)) {
      setIsPolling(false);
    }
  }, [agent?.status]);

  const handleSend = async (prompt: string) => {
    setIsPolling(true);
    await startRun(agentId, prompt);
    await fetchMessages(agentId);
    await refreshAgent(agentId);
  };

  if (!agent) return null;

  const isBusy = ACTIVE_STATUSES.has(agent.status);

  return (
    <div className="fixed right-0 top-0 h-full w-[420px] bg-neutral-950 border-l border-neutral-800 shadow-2xl flex flex-col z-50">
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800">
        <div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isBusy ? "bg-amber-400 animate-pulse" : agent.status === "error" ? "bg-red-500" : "bg-emerald-500"}`} />
            <h2 className="text-sm font-semibold text-white">{agent.name}</h2>
          </div>
          <p className="text-xs text-neutral-500">{agent.model} · {agent.status}</p>
        </div>
        <button onClick={onClose} className="text-neutral-400 hover:text-white text-lg leading-none">
          ×
        </button>
      </div>

      <div className="flex border-b border-neutral-800">
        {(["chat", "reasoning", "settings"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 text-xs font-medium capitalize transition-colors ${
              tab === t ? "text-white border-b-2 border-purple-500" : "text-neutral-500 hover:text-neutral-300"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {tab === "chat" && (
          <>
            <ChatMessages messages={messages} />
            <ChatInput disabled={isBusy} onSend={handleSend} />
          </>
        )}
        {tab === "reasoning" && <ReasoningPanel messages={messages} />}
        {tab === "settings" && (
          <div className="flex-1 overflow-y-auto py-4">
            <AgentSettingsForm
              agentId={agentId}
              initialValues={agent}
              onSaved={() => refreshAgent(agentId)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
