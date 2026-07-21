import { useMemo, useState } from "react";
import { agentsApi } from "../api/agents";
import { buildAgentSettingsPayload, type AgentSettingsFormValues } from "../api/agentSettingsUtils";
import type { Agent } from "../api/types";

const defaultValues: AgentSettingsFormValues = {
  temperature: "",
  max_tokens: "",
  system_prompt: "",
};

function deriveInitialValues(initial?: Partial<Agent>): AgentSettingsFormValues {
  const settings = (initial?.settings ?? {}) as Record<string, unknown>;
  return {
    ...defaultValues,
    temperature: (settings.temperature as string) ?? "",
    max_tokens: (settings.num_predict as string) ?? "",
    system_prompt: initial?.system_prompt ?? "",
  };
}

interface Props {
  agentId: string;
  initialValues?: Partial<Agent>;
  onSaved?: (agent: Agent) => void;
}

export default function AgentSettingsForm({ agentId, initialValues, onSaved }: Props) {
  const [formValues, setFormValues] = useState<AgentSettingsFormValues>(() =>
    deriveInitialValues(initialValues)
  );
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const settingsPreview = useMemo(() => {
    try {
      return buildAgentSettingsPayload(formValues);
    } catch {
      return null;
    }
  }, [formValues]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormValues((current) => ({ ...current, [name]: value }));
    setStatus("idle");
    setMessage("");
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setError("");
    setMessage("");
    try {
      const payload = buildAgentSettingsPayload(formValues);
      const updated = await agentsApi.update(agentId, payload);
      setStatus("success");
      setMessage("Agent settings saved successfully.");
      onSaved?.(updated);
    } catch (err) {
      setStatus("error");
      setError((err as Error).message || "Unexpected error while saving settings");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-lg mx-auto p-6 rounded-2xl bg-neutral-950 text-neutral-100 shadow-lg ring-1 ring-white/10">
      <h2 className="text-lg font-semibold mb-1">Editable Agent Settings</h2>
      <p className="text-sm text-neutral-400 mb-4">Tune the agent behavior for Ollama-compatible requests.</p>

      <label className="block mb-3">
        <span className="block mb-1 text-sm">Temperature</span>
        <input
          name="temperature"
          type="number"
          min="0"
          max="1"
          step="0.01"
          value={formValues.temperature}
          onChange={handleChange}
          placeholder="0.2"
          className="w-full px-3 py-2 rounded-lg border border-neutral-700 bg-neutral-900 text-sm"
        />
      </label>

      <label className="block mb-3">
        <span className="block mb-1 text-sm">Max Tokens</span>
        <input
          name="max_tokens"
          type="number"
          min="1"
          step="1"
          value={formValues.max_tokens}
          onChange={handleChange}
          placeholder="256"
          className="w-full px-3 py-2 rounded-lg border border-neutral-700 bg-neutral-900 text-sm"
        />
      </label>

      <label className="block mb-4">
        <span className="block mb-1 text-sm">System Prompt</span>
        <textarea
          name="system_prompt"
          rows={6}
          value={formValues.system_prompt}
          onChange={handleChange}
          placeholder="You are a helpful assistant..."
          className="w-full px-3 py-2 rounded-lg border border-neutral-700 bg-neutral-900 text-sm resize-y min-h-[120px]"
        />
      </label>

      <div className="mb-3 p-3 rounded-lg bg-neutral-900">
        <div className="text-xs text-neutral-400">Payload preview</div>
        <pre className="mt-1 whitespace-pre-wrap text-sm">
          {settingsPreview ? JSON.stringify(settingsPreview, null, 2) : "Fix the highlighted values to continue."}
        </pre>
      </div>

      <button
        type="submit"
        disabled={status === "loading"}
        className="w-full py-3 rounded-lg font-semibold text-white bg-purple-600 hover:bg-purple-500 disabled:bg-neutral-700 disabled:cursor-wait transition-colors"
      >
        {status === "loading" ? "Saving…" : "Save Settings"}
      </button>

      {message && <p className="mt-3 text-sm text-emerald-400">{message}</p>}
      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
    </form>
  );
}
