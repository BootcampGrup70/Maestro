import type { ToolCall, ToolCallStatus } from "../api/types";

interface Props {
  toolCalls: ToolCall[];
}

function statusStyles(status: ToolCallStatus) {
  switch (status) {
    case "success":
      return "text-emerald-400 border-emerald-700/50 bg-emerald-900/20";
    case "error":
      return "text-red-400 border-red-700/50 bg-red-900/20";
    default:
      return "text-amber-400 border-amber-700/50 bg-amber-900/20";
  }
}

export default function ToolCallsPanel({ toolCalls }: Props) {
  if (toolCalls.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-neutral-500 text-sm">
        Henüz bir tool call yok.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      {toolCalls.map((tc) => (
        <div key={tc.id} className="rounded-lg bg-neutral-900 border border-neutral-800 p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-mono text-neutral-400">
              {tc.tool_name}.{tc.operation}
              {typeof tc.arguments.path === "string" ? ` — ${tc.arguments.path}` : ""}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full border ${statusStyles(tc.status)}`}>
              {tc.status}
            </span>
          </div>
          {tc.result && (
            <pre className="whitespace-pre-wrap text-xs text-neutral-300 font-mono mt-1">
              {tc.result}
            </pre>
          )}
          {tc.error_message && (
            <pre className="whitespace-pre-wrap text-xs text-red-300 font-mono mt-1">
              {tc.error_message}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}
