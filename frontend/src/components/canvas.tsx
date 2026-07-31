import { useCallback, useEffect } from "react";
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
    <div
      style={{
        background: "#1f2937",
        border: `2px solid ${color}`,
        borderRadius: "10px",
        padding: "12px 16px",
        minWidth: "160px",
        color: "#f9fafb",
        fontSize: "13px",
        position: "relative",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: "4px" }}>
        {data.name as string}
      </div>
      <div style={{ color, fontSize: "11px", textTransform: "uppercase" }}>
        {status}
      </div>
      <button
        onClick={handleDelete}
        style={{
          position: "absolute",
          top: "6px",
          right: "6px",
          background: "transparent",
          border: "none",
          color: "#ef4444",
          cursor: "pointer",
          fontSize: "14px",
          lineHeight: 1,
          padding: "2px 4px",
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
  const createAgent = useAppStore((s) => s.createAgent);
  const removeAgent = useAppStore((s) => s.removeAgent);
  const updateAgentPosition = useAppStore((s) => s.updateAgentPosition);
  const selectAgent = useAppStore((s) => s.selectAgent);

  const { send } = useWebSocket();

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    const newNodes: Node[] = agents.map((agent) => ({
      id: agent.id,
      type: "agentNode",
      position: { x: agent.canvas_x ?? 100, y: agent.canvas_y ?? 100 },
      data: {
        id: agent.id,
        name: agent.name,
        status: agent.status,
        error_message: agent.error_message,
      },
    }));
    setNodes(newNodes);
  }, [agents, setNodes]);

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges]
  );

  const onNodeDragStop = useCallback(
    (_: unknown, node: Node) => {
      updateAgentPosition(node.id, node.position.x, node.position.y);
    },
    [updateAgentPosition]
  );

  const onNodesDelete = useCallback(
    (deleted: Node[]) => {
      for (const node of deleted) {
        removeAgent(node.id);
        selectAgent(null);
        setEdges((eds) =>
          eds.filter((e) => e.source !== node.id && e.target !== node.id)
        );
      }
    },
    [removeAgent, selectAgent, setEdges]
  );

  const onNodeClick = useCallback(
    (_: unknown, node: Node) => {
      selectAgent(node.id);
    },
    [selectAgent]
  );

  const handleAddAgent = async () => {
    const name = prompt("Ajan adı:");
    if (!name) return;
    await createAgent({ name, model: "llama3.2" });
  };

  const handleInterject = useCallback(
    (agentId: string, content: string) => {
      send({ type: "interject", agent_id: agentId, content });
    },
    [send]
  );

  void handleInterject;

  return (
    <div style={{ width: "100%", height: "100vh", background: "#050608" }}>
      <button
        onClick={handleAddAgent}
        style={{
          position: "absolute",
          top: "16px",
          left: "16px",
          zIndex: 10,
          background: "#3b82f6",
          color: "white",
          border: "none",
          borderRadius: "6px",
          padding: "8px 16px",
          cursor: "pointer",
          fontSize: "14px",
        }}
      >
        + Ajan Ekle
      </button>

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
    </div>
  );
}