import { useState } from "react";

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "#1f2937",
  border: "1px solid #374151",
  borderRadius: "6px",
  padding: "8px 12px",
  color: "#f9fafb",
  fontSize: "14px",
  boxSizing: "border-box",
};

export default function SettingsPage() {
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [concurrency, setConcurrency] = useState(3);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={{ padding: "40px", maxWidth: "600px", color: "#f9fafb" }}>
      <h1 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "32px" }}>Settings</h1>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{
          fontSize: "12px", fontWeight: 600, color: "#6b7280",
          textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px",
        }}>
          Ollama Connection
        </h2>
        <div style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: "10px", padding: "20px" }}>
          <label style={{ display: "block" }}>
            <span style={{ fontSize: "13px", color: "#9ca3af", display: "block", marginBottom: "6px" }}>API URL</span>
            <input value={ollamaUrl} onChange={(e) => setOllamaUrl(e.target.value)} style={inputStyle} />
          </label>
        </div>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{
          fontSize: "12px", fontWeight: 600, color: "#6b7280",
          textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px",
        }}>
          Execution
        </h2>
        <div style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: "10px", padding: "20px" }}>
          <label style={{ display: "block" }}>
            <span style={{ fontSize: "13px", color: "#9ca3af", display: "block", marginBottom: "6px" }}>
              Max Concurrent Agents
            </span>
            <input
              type="number"
              min={1}
              max={10}
              value={concurrency}
              onChange={(e) => setConcurrency(Number(e.target.value))}
              style={{ ...inputStyle, width: "80px" }}
            />
          </label>
        </div>
      </section>

      <button
        onClick={handleSave}
        style={{
          background: "#3b82f6", border: "none", color: "white",
          borderRadius: "6px", padding: "10px 24px", cursor: "pointer", fontSize: "14px",
        }}
      >
        {saved ? "Saved ✓" : "Save Changes"}
      </button>
    </div>
  );
}