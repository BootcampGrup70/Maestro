import { useEffect } from "react";
import { useAppStore } from "./store/useAppStore";

function App() {
  const { agents, agentsLoading, agentsError, fetchAgents } = useAppStore();

  useEffect(() => {
    fetchAgents();
  }, []);

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-8">
      <h1 className="text-2xl font-bold text-purple-400 mb-4">Store Test</h1>
      {agentsLoading && <p>Yukleniyor...</p>}
      {agentsError && <p className="text-red-400">Hata: {agentsError}</p>}
      {!agentsLoading && !agentsError && (
        <p>{agents.length} agent bulundu:</p>
      )}
      <ul className="mt-2 space-y-1">
        {agents.map((a) => (
          <li key={a.id} className="text-sm text-neutral-300">
            {a.name} — {a.model} — {a.status}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
