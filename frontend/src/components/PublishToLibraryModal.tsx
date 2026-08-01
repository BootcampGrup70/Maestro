import { useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { LIBRARY_TAGS } from "../api/library";

interface Props {
  initialSelectedIds: string[];
  onClose: () => void;
  onPublished: () => void;
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

function tagPillStyle(active: boolean): React.CSSProperties {
  return {
    display: "inline-block",
    cursor: "pointer",
    userSelect: "none",
    fontSize: "12px",
    fontWeight: 600,
    padding: "4px 10px",
    borderRadius: "99px",
    background: active ? "#3b82f622" : "transparent",
    color: active ? "#3b82f6" : "#9ca3af",
    border: `1px solid ${active ? "#3b82f644" : "#374151"}`,
  };
}

export default function PublishToLibraryModal({ initialSelectedIds, onClose, onPublished }: Props) {
  const agents = useAppStore((s) => s.agents);
  const publishWorkflow = useAppStore((s) => s.publishWorkflow);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set(initialSelectedIds));
  const [loading, setLoading] = useState(false);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => {
      const next = new Set(prev);
      if (next.has(tag)) next.delete(tag);
      else next.add(tag);
      return next;
    });
  };

  const toggleAgent = (id: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const canSubmit = name.trim() && checkedIds.size > 0 && !loading;

  const handlePublish = async () => {
    if (!canSubmit) return;
    setLoading(true);
    try {
      await publishWorkflow({
        name: name.trim(),
        description: description.trim() || undefined,
        tags: Array.from(selectedTags),
        agent_ids: Array.from(checkedIds),
      });
      onPublished();
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
        <h2 style={{ margin: "0 0 4px", fontSize: "18px", fontWeight: 600 }}>Publish to Library</h2>
        <div style={{ fontSize: "11px", color: "#6b7280", marginBottom: "20px" }}>
          {checkedIds.size} agent{checkedIds.size === 1 ? "" : "s"} selected
        </div>

        <label style={{ display: "block", marginBottom: "16px" }}>
          <span style={{ fontSize: "13px", color: "#9ca3af", display: "block", marginBottom: "6px" }}>Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Workflow name"
            style={inputStyle}
          />
        </label>

        <label style={{ display: "block", marginBottom: "16px" }}>
          <span style={{ fontSize: "13px", color: "#9ca3af", display: "block", marginBottom: "6px" }}>Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description..."
            rows={3}
            style={{ ...inputStyle, resize: "vertical" }}
          />
        </label>

        <div style={{ marginBottom: "16px" }}>
          <span style={{ fontSize: "13px", color: "#9ca3af", display: "block", marginBottom: "6px" }}>Tags</span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {LIBRARY_TAGS.map((tag) => (
              <span key={tag} onClick={() => toggleTag(tag)} style={tagPillStyle(selectedTags.has(tag))}>
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: "24px" }}>
          <span style={{ fontSize: "13px", color: "#9ca3af", display: "block", marginBottom: "6px" }}>Agents to publish</span>
          <div style={{
            border: "1px solid #374151", borderRadius: "6px", maxHeight: "180px", overflowY: "auto",
          }}>
            {agents.length === 0 && (
              <div style={{ padding: "12px", fontSize: "13px", color: "#6b7280" }}>No agents on the canvas yet.</div>
            )}
            {agents.map((agent) => (
              <label
                key={agent.id}
                style={{
                  display: "flex", alignItems: "center", gap: "8px",
                  padding: "8px 12px", fontSize: "13px", cursor: "pointer",
                  borderBottom: "1px solid #1f2937",
                }}
              >
                <input
                  type="checkbox"
                  checked={checkedIds.has(agent.id)}
                  onChange={() => toggleAgent(agent.id)}
                />
                <span style={{ flex: 1 }}>{agent.name}</span>
                <span style={{ color: "#6b7280", fontSize: "11px" }}>{agent.model}</span>
              </label>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{
            background: "transparent", border: "1px solid #374151", color: "#9ca3af",
            borderRadius: "6px", padding: "8px 20px", cursor: "pointer", fontSize: "14px",
          }}>Cancel</button>
          <button onClick={handlePublish} disabled={!canSubmit} style={{
            background: "#3b82f6", border: "none", color: "white",
            borderRadius: "6px", padding: "8px 20px", cursor: "pointer", fontSize: "14px",
            opacity: !canSubmit ? 0.5 : 1,
          }}>
            {loading ? "Publishing..." : "Publish"}
          </button>
        </div>
      </div>
    </div>
  );
}
