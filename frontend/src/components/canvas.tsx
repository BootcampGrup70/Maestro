import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  type Connection,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useAppStore } from "../store/useAppStore";
import { useWebSocket } from "../hooks/useWebSocket";
import CreateAgentModal from "./CreateAgentModal";

const STATUS_COLOR: Record<string, string> = {
  idle: "#6b7280",
  thinking: "#3b82f6",
  tool_calling: "#f59e0b",
  done: "#22c55e",
  error: "#ef4444",
  queued: "#a855f7",
};

function AgentNode({ data }: { data: Record<string, unknown> }) {
  const status = (data.status as string) ?? "idle";
  const color = STATUS_COLOR[status] ?? "#6b7280";
  const removeAgent = useAppStore((s) => s.removeAgent);
  const selectAgent = useAppStore((s) => s.selectAgent);

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`"${data.name}" ajanı silinsin mi?`)) {
      await removeAgent(data.id as string);
      selectAgent(null);
    }
  };

  return (
    <div style={{
      background: "#1f2937",
      border: `2px solid ${color}`,
      borderRadius: "10px",
      padding: "12px 16px",
      minWidth: "180px",
      color: "#f9fafb",
      fontSize: "13px",
      position: "relative",
    }}>
      <div style={{ fontWeight: 600, marginBottom: "2px" }}>{data.name as string}</div>
      <div style={{ fontSize: "11px", color: "#6b7280", marginBottom: "6px" }}>{data.model as string}</div>
      <div style={{
        display: "inline-block",
        background: color + "22",
        color,
        fontSize: "10px",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        padding: "2px 8px",
        borderRadius: "99px",
        border: `1px solid ${color}44`,
      }}>
        {status}
      </div>
      <button
        onClick={handleDelete}
        style={{
          position: "absolute", top: "6px", right: "6px",
          background: "transparent", border: "none", color: "#4b5563",
          cursor: "pointer", fontSize: "14px", lineHeight: 1, padding: "2px 4px",
        }}
      >
        ✕
      </button>
    </div>
  );
}

const nodeTypes = { agentNode: AgentNode };

export default function Canvas() {
  const agents = useAppStore((s) => s.agents);
  const fetchAgents = useAppStore((s) => s.fetchAgents);
  const removeAgent = useAppStore((s) => s.removeAgent);
  const updateAgentPosition = useAppStore((s) => s.updateAgentPosition);
  const selectAgent = useAppStore((s) => s.selectAgent);
  const [showModal, setShowModal] = useState(false);

  const { send } = useWebSocket();
  void send;

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  useEffect(() => {
    setNodes(agents.map((agent) => ({
      id: agent.id,
      type: "agentNode",
      position: { x: agent.canvas_x ?? 100, y: agent.canvas_y ?? 100 },
      data: {
        id: agent.id,
        name: agent.name,
        model: agent.model ?? "llama3.2",
        status: agent.status,
        error_message: agent.error_message,
      },
    })));
  }, [agents, setNodes]);

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges]
  );

  const onNodeDragStop = useCallback(
    (_: unknown, node: Node) => updateAgentPosition(node.id, node.position.x, node.position.y),
    [updateAgentPosition]
  );

  const onNodesDelete = useCallback(
    (deleted: Node[]) => {
      for (const node of deleted) {
        removeAgent(node.id);
        selectAgent(null);
        setEdges((eds) => eds.filter((e) => e.source !== node.id && e.target !== node.id));
      }
    },
    [removeAgent, selectAgent, setEdges]
  );

  const onNodeClick = useCallback(
    (_: unknown, node: Node) => selectAgent(node.id),
    [selectAgent]
  );

  return (
    <div style={{ width: "100%", height: "100vh", background: "#050608", position: "relative" }}>
      <button
        onClick={() => setShowModal(true)}
        style={{
          position: "absolute", top: "16px", left: "16px", zIndex: 10,
          background: "#3b82f6", color: "white", border: "none",
          borderRadius: "6px", padding: "8px 16px", cursor: "pointer", fontSize: "14px",
        }}
      >
        + Create Agent
      </button>

      {agents.length === 0 && (
        <div style={{
          position: "absolute", inset: 0, display: "flex",
          flexDirection: "column", alignItems: "center", justifyContent: "center",
          color: "#374151", pointerEvents: "none", zIndex: 5,
        }}>
          <div style={{ fontSize: "48px", marginBottom: "16px" }}>◈</div>
          <div style={{ fontSize: "18px", fontWeight: 600, marginBottom: "8px" }}>No agents yet</div>
          <div style={{ fontSize: "14px" }}>Click "Create Agent" to get started</div>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeDragStop={onNodeDragStop}
        onNodesDelete={onNodesDelete}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
      >
        <Controls />
        <Background color="#1f2937" gap={20} />
      </ReactFlow>

      {showModal && <CreateAgentModal onClose={() => setShowModal(false)} />}
    </div>
  );
}