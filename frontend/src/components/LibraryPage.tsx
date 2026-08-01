import { useEffect, useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { libraryApi, LIBRARY_TAGS } from "../api/library";
import type { LibraryAgentRead, LibraryWorkflow } from "../api/types";

interface Props {
  onImported: () => void;
}

const inputStyle: React.CSSProperties = {
  background: "#1f2937",
  border: "1px solid #374151",
  borderRadius: "6px",
  padding: "8px 12px",
  color: "#f9fafb",
  fontSize: "14px",
  boxSizing: "border-box",
  fontFamily: "inherit",
};

const IMPORT_OFFSET = { offset_x: 60, offset_y: 60 };

function WorkflowCard({ workflow, onImported }: { workflow: LibraryWorkflow; onImported: () => void }) {
  const importWorkflow = useAppStore((s) => s.importWorkflow);
  const [expanded, setExpanded] = useState(false);
  const [agents, setAgents] = useState<LibraryAgentRead[] | null>(null);
  const [importing, setImporting] = useState(false);

  const toggleExpanded = async () => {
    if (!expanded && agents === null) {
      const detail = await libraryApi.get(workflow.id);
      setAgents(detail.agents);
    }
    setExpanded((v) => !v);
  };

  const handleImport = async () => {
    setImporting(true);
    try {
      await importWorkflow(workflow.id, IMPORT_OFFSET);
      onImported();
    } finally {
      setImporting(false);
    }
  };

  return (
    <div style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: "10px", padding: "16px" }}>
      <div style={{ fontWeight: 600, fontSize: "15px", marginBottom: "4px" }}>{workflow.name}</div>
      {workflow.description && (
        <div style={{
          fontSize: "13px", color: "#9ca3af", marginBottom: "8px",
          display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
        }}>
          {workflow.description}
        </div>
      )}

      {workflow.tags.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "10px" }}>
          {workflow.tags.map((tag) => (
            <span key={tag} style={{
              display: "inline-block", background: "#3b82f622", color: "#3b82f6",
              fontSize: "10px", fontWeight: 600, padding: "2px 8px", borderRadius: "99px",
              border: "1px solid #3b82f644",
            }}>
              {tag}
            </span>
          ))}
        </div>
      )}

      <div style={{ fontSize: "12px", color: "#6b7280", marginBottom: "10px" }}>
        {workflow.agent_count} agent{workflow.agent_count === 1 ? "" : "s"} · imported {workflow.import_count}× · {new Date(workflow.created_at).toLocaleDateString()}
      </div>

      <button
        onClick={toggleExpanded}
        style={{
          background: "transparent", border: "none", color: "#9ca3af", cursor: "pointer",
          fontSize: "12px", padding: 0, marginBottom: "10px",
        }}
      >
        {expanded ? "▾" : "▸"} {workflow.agent_count} agent{workflow.agent_count === 1 ? "" : "s"}
      </button>

      {expanded && agents && (
        <div style={{ marginBottom: "10px", fontSize: "12px", color: "#d1d5db" }}>
          {agents.map((a) => (
            <div key={a.id} style={{ padding: "2px 0" }}>
              {a.parent_local_ref ? "↳ " : ""}{a.name} · {a.model}
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button onClick={handleImport} disabled={importing} style={{
          background: "#3b82f6", border: "none", color: "white",
          borderRadius: "6px", padding: "6px 14px", cursor: "pointer", fontSize: "13px",
          opacity: importing ? 0.5 : 1,
        }}>
          {importing ? "Importing..." : "Import"}
        </button>
      </div>
    </div>
  );
}

export default function LibraryPage({ onImported }: Props) {
  const libraryWorkflows = useAppStore((s) => s.libraryWorkflows);
  const libraryLoading = useAppStore((s) => s.libraryLoading);
  const libraryError = useAppStore((s) => s.libraryError);
  const fetchLibraryWorkflows = useAppStore((s) => s.fetchLibraryWorkflows);

  const [search, setSearch] = useState("");
  const [tag, setTag] = useState("");

  useEffect(() => {
    const timeout = setTimeout(() => {
      fetchLibraryWorkflows({ search: search || undefined, tag: tag || undefined });
    }, 300);
    return () => clearTimeout(timeout);
  }, [search, tag, fetchLibraryWorkflows]);

  return (
    <div style={{ padding: "40px", color: "#f9fafb", height: "100vh", overflowY: "auto", boxSizing: "border-box" }}>
      <h1 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "24px" }}>Library</h1>

      <div style={{ display: "flex", gap: "12px", marginBottom: "24px" }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search workflows..."
          style={{ ...inputStyle, flex: 1 }}
        />
        <select
          value={tag}
          onChange={(e) => setTag(e.target.value)}
          style={{ ...inputStyle, width: "180px" }}
        >
          <option value="">All tags</option>
          {LIBRARY_TAGS.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {libraryLoading && libraryWorkflows.length === 0 && (
        <div style={{ color: "#6b7280", fontSize: "14px" }}>Loading...</div>
      )}

      {libraryError && (
        <div style={{ color: "#ef4444", fontSize: "14px", marginBottom: "16px" }}>{libraryError}</div>
      )}

      {!libraryLoading && libraryWorkflows.length === 0 && !libraryError && (
        <div style={{ color: "#6b7280", fontSize: "14px" }}>No published workflows yet.</div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "16px" }}>
        {libraryWorkflows.map((workflow) => (
          <WorkflowCard key={workflow.id} workflow={workflow} onImported={onImported} />
        ))}
      </div>
    </div>
  );
}
