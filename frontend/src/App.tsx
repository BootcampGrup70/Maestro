import { useState } from "react";
import { useAppStore } from "./store/useAppStore";
import Canvas from "./components/canvas";
import AgentDetailPanel from "./components/AgentDetailPanel";
import Sidebar from "./components/Sidebar";
import SettingsPage from "./components/SettingsPage";

type View = "orchestrate" | "settings";

function App() {
  const [view, setView] = useState<View>("orchestrate");
  const selectedAgentId = useAppStore((s) => s.selectedAgentId);
  const selectAgent = useAppStore((s) => s.selectAgent);

  return (
    <div style={{ display: "flex", width: "100vw", height: "100vh", background: "#050608", overflow: "hidden" }}>
      <Sidebar activeView={view} onViewChange={setView} />

      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {view === "orchestrate" && <Canvas />}
        {view === "settings" && <SettingsPage />}
      </div>

      {selectedAgentId && view === "orchestrate" && (
        <div style={{
          width: "380px",
          height: "100vh",
          background: "#111827",
          borderLeft: "1px solid #1f2937",
          overflowY: "auto",
          flexShrink: 0,
        }}>
          <AgentDetailPanel agentId={selectedAgentId} onClose={() => selectAgent(null)} />
        </div>
      )}
    </div>
  );
}

export default App;