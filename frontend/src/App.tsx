import { useAppStore } from "./store/useAppStore";
import Canvas from "./components/canvas";
import AgentDetailPanel from "./components/AgentDetailPanel";

function App() {
  const selectedAgentId = useAppStore((s) => s.selectedAgentId);
  const selectAgent = useAppStore((s) => s.selectAgent);

  return (
    <div style={{ width: "100vw", height: "100vh", background: "#050608" }}>
      <Canvas />
      {selectedAgentId && (
        <div
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            height: "100vh",
            width: "380px",
            zIndex: 20,
            background: "#111827",
            borderLeft: "1px solid #1f2937",
            overflowY: "auto",
          }}
        >
          <AgentDetailPanel
            agentId={selectedAgentId}
            onClose={() => selectAgent(null)}
          />
        </div>
      )}
    </div>
  );
}

export default App;