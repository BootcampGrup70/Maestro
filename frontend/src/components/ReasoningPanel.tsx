import type { Message } from "../api/types";
import { splitThinking } from "../api/parseThinking";

interface Props {
  messages: Message[];
  streamingThinking?: string;
}

export default function ReasoningPanel({ messages, streamingThinking }: Props) {
  const withThinking = messages
    .map((m) => ({
      message: m,
      thinking: m.thinking || splitThinking(m.content).thinking,
    }))
    .filter((x) => x.thinking);

  if (withThinking.length === 0 && !streamingThinking) {
    return (
      <div className="flex-1 flex items-center justify-center text-neutral-500 text-sm">
        Henüz bir reasoning (thinking) verisi yok.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      {withThinking.map(({ message: m, thinking }) => (
        <div key={m.id} className="rounded-lg bg-neutral-900 border border-neutral-800 p-3">
          <div className="text-xs text-neutral-500 mb-1">Mesaj #{m.seq} — {m.role}</div>
          <pre className="whitespace-pre-wrap text-xs text-neutral-300 font-mono">{thinking}</pre>
        </div>
      ))}

      {streamingThinking && (
        <div className="rounded-lg bg-neutral-900 border border-purple-800/50 p-3">
          <div className="text-xs text-purple-400 mb-1">Şu an düşünüyor...</div>
          <pre className="whitespace-pre-wrap text-xs text-neutral-300 font-mono">{streamingThinking}</pre>
        </div>
      )}
    </div>
  );
}
