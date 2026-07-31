import { useEffect } from "react";
import { useAppStore } from "./store/useAppStore";
import AgentDetailPanel from "./components/AgentDetailPanel";

function App() {
  const { agents, fetchAgents, selectedAgentId, selectAgent } = useAppStore();

  useEffect(() => {
    fetchAgents();
  }, []);

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-8">
      <h1 className="text-xl font-bold text-purple-400 mb-4">Agents</h1>
      <ul className="space-y-2">
        {agents.map((a) => (
          <li
            key={a.id}
            onClick={() => selectAgent(a.id)}
            className="cursor-pointer px-3 py-2 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-sm"
          >
            {a.name} — {a.model} — {a.status}
          </li>
        ))}
      </ul>

      {selectedAgentId && (
        <AgentDetailPanel agentId={selectedAgentId} onClose={() => selectAgent(null)} />
      )}
    </div>
  );
}

export default App;
