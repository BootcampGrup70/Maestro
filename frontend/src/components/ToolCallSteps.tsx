import type { ToolCallState } from "../store/useAppStore";

interface Props {
  toolCalls: ToolCallState[];
}

function statusColor(status: string) {
  if (status === "success") return "text-emerald-400";
  if (status === "error") return "text-red-400";
  return "text-amber-400";
}

export default function ToolCallSteps({ toolCalls }: Props) {
  if (toolCalls.length === 0) return null;

  return (
    <div className="px-4 py-2 space-y-1 border-t border-neutral-800">
      <div className="text-xs text-neutral-500 mb-1">Tool calls</div>
      {toolCalls.map((tc) => (
        <div key={tc.id} className="flex items-center justify-between text-xs bg-neutral-900 rounded px-2 py-1">
          <span className="text-neutral-300">{tc.operation}</span>
          <span className={statusColor(tc.status)}>{tc.status}</span>
        </div>
      ))}
    </div>
  );
}
