import React from 'react';
import AgentSettingsForm from './AgentSettingsForm';

export default function App() {
  return (
    <div style={{ minHeight: '100vh', background: '#050608', padding: '2rem 1rem' }}>
      <AgentSettingsForm agentId="demo-agent" />
    </div>
  );
}
