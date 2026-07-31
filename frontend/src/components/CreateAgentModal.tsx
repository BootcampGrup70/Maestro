import { useState, useEffect } from "react";
import { useAppStore } from "../store/useAppStore";

interface Props {
  onClose: () => void;
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "#1f2937",
  border: "1px solid #374151",
  borderRadius: "6px",
  padding: "8px 12px",
  color: "#f9fafb",
  fontSize: "14px",
  boxSizing: "border-box",
  fontFamily: "inherit",
};

const SUGGESTED_MODELS = [
  "llama3.2:latest",
  "llama3.1:latest",
  "mistral:latest",
  "deepseek-r1:latest",
  "qwen2.5:latest",
  "gemma3:1b",
];

export default function CreateAgentModal({ onClose }: Props) {
  const createAgent = useAppStore((s) => s.createAgent);
  const [name, setName] = useState("");
  const [model, setModel] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<string[]>([]);
  const [available, setAvailable] = useState<string[]>([]);

  useEffect(() => {
    fetch("http://localhost:8000/api/agents/available-models")
      .then((r) => r.json())
      .then((data: string[]) => {
        const notInstalled = SUGGESTED_MODELS.filter((m) => !data.includes(m));
        const combined = [...data, ...notInstalled];
        setModels(combined);
        setAvailable(data);
        if (data.length > 0) setModel(data[0]);
      })
      .catch(() => {
        setModels(SUGGESTED_MODELS);
        setAvailable([]);
        setModel(SUGGESTED_MODELS[0]);
      });
  }, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setLoading(true);
    try {
      await createAgent({ name: name.trim(), model, system_prompt: systemPrompt || undefined });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
    }}>
      <div style={{
        background: "#111827", borderRadius: "12px", padding: "28px",
        width: "480px", border: "1px solid #1f2937", color: "#f9fafb",
      }}>
        <h2 style={{ margin: "0 0 24px", fontSize: "18px", fontWeight: 600 }}>Create Agent</h2>

        <label style={{ display: "block", marginBottom: "16px" }}>
          <span style={{ fontSize: "13px", color: "#9ca3af", display: "block", marginBottom: "6px" }}>Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Agent name"
            style={inputStyle}
          />
        </label>

        <label style={{ display: "block", marginBottom: "16px" }}>
          <span style={{ fontSize: "13px", color: "#9ca3af", display: "block", marginBottom: "6px" }}>Model</span>
          <select value={model} onChange={(e) => setModel(e.target.value)} style={inputStyle}>
            {models.map((m) => (
              <option key={m} value={m}>
                {available.includes(m) ? `✓ ${m}` : m}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "block", marginBottom: "24px" }}>
          <span style={{ fontSize: "13px", color: "#9ca3af", display: "block", marginBottom: "6px" }}>System Prompt</span>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Optional system prompt..."
            rows={4}
            style={{ ...inputStyle, resize: "vertical" }}
          />
        </label>

        <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{
            background: "transparent", border: "1px solid #374151", color: "#9ca3af",
            borderRadius: "6px", padding: "8px 20px", cursor: "pointer", fontSize: "14px",
          }}>Cancel</button>
          <button onClick={handleCreate} disabled={!name.trim() || loading || !model} style={{
            background: "#3b82f6", border: "none", color: "white",
            borderRadius: "6px", padding: "8px 20px", cursor: "pointer", fontSize: "14px",
            opacity: !name.trim() || loading || !model ? 0.5 : 1,
          }}>
            {loading ? "Creating..." : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}