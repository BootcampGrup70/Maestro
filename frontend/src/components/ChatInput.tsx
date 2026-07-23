import { useState } from "react";

interface Props {
  disabled?: boolean;
  onSend: (prompt: string) => void;
}

export default function ChatInput({ disabled, onSend }: Props) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2 p-3 border-t border-neutral-800">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            handleSubmit(e);
          }
        }}
        placeholder="Send a message..."
        rows={1}
        disabled={disabled}
        className="flex-1 resize-none px-3 py-2 rounded-lg border border-neutral-700 bg-neutral-900 text-sm text-neutral-100 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:bg-neutral-700 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors"
      >
        Gönder
      </button>
    </form>
  );
}
