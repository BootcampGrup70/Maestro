import type { Message } from "../api/types";
import { splitThinking } from "../api/parseThinking";

interface Props {
  messages: Message[];
}

function roleStyles(role: Message["role"]) {
  switch (role) {
    case "user":
      return "ml-auto bg-purple-600 text-white";
    case "assistant":
      return "mr-auto bg-neutral-800 text-neutral-100";
    case "tool":
      return "mr-auto bg-amber-900/40 text-amber-200 border border-amber-700/50";
    case "system":
      return "mx-auto bg-neutral-900 text-neutral-500 text-xs italic";
    default:
      return "mr-auto bg-neutral-800 text-neutral-100";
  }
}

export default function ChatMessages({ messages }: Props) {
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-neutral-500 text-sm">
        Henüz mesaj yok. Aşağıdan bir talimat gönderin.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      {messages.map((m) => {
        const { content } = splitThinking(m.content);
        return (
          <div key={m.id} className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${roleStyles(m.role)}`}>
            {m.role === "tool" && (
              <div className="text-xs font-semibold mb-1 uppercase tracking-wide">Tool result</div>
            )}
            <div className="whitespace-pre-wrap">{content || "(boş cevap)"}</div>
          </div>
        );
      })}
    </div>
  );
}
