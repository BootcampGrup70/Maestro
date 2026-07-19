import React, { useMemo, useState } from 'react';
import { buildAgentSettingsPayload } from './agentSettingsUtils';

const defaultValues = {
  temperature: '',
  max_tokens: '',
  system_prompt: '',
};

function deriveInitialValues(initialValues = {}) {
  const settings = initialValues.settings || {};
  return {
    ...defaultValues,
    temperature: initialValues.temperature ?? settings.temperature ?? '',
    max_tokens: initialValues.max_tokens ?? settings.num_predict ?? '',
    system_prompt: initialValues.system_prompt ?? '',
  };
}

export default function AgentSettingsForm({ agentId, initialValues = {}, onSaved }) {
  const [formValues, setFormValues] = useState(() => deriveInitialValues(initialValues));
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const settingsPreview = useMemo(() => {
    try {
      return buildAgentSettingsPayload(formValues);
    } catch {
      return null;
    }
  }, [formValues]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormValues((current) => ({ ...current, [name]: value }));
    setStatus('idle');
    setMessage('');
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus('loading');
    setError('');
    setMessage('');

    try {
      const payload = buildAgentSettingsPayload(formValues);
      const response = await fetch(`/api/agents/${agentId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const responseData = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(responseData.detail || 'Unable to save agent settings');
      }

      setStatus('success');
      setMessage('Agent settings saved successfully.');
      if (onSaved) {
        onSaved(responseData);
      }
    } catch (submitError) {
      setStatus('error');
      setError(submitError.message || 'Unexpected error while saving settings');
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        maxWidth: 560,
        margin: '2rem auto',
        padding: '1.5rem',
        borderRadius: '16px',
        background: '#0b0b0d',
        color: '#f5f5f5',
        boxShadow: '0 0 0 1px rgba(255,255,255,0.08), 0 12px 40px rgba(0,0,0,0.35)',
      }}
    >
      <h2 style={{ marginTop: 0, marginBottom: '0.25rem', fontSize: '1.25rem' }}>Editable Agent Settings</h2>
      <p style={{ marginTop: 0, marginBottom: '1rem', color: '#b8c0cc' }}>
        Tune the agent behavior for Ollama-compatible requests.
      </p>

      <label style={{ display: 'block', marginBottom: '0.75rem' }}>
        <span style={{ display: 'block', marginBottom: '0.35rem' }}>Temperature</span>
        <input
          name="temperature"
          type="number"
          min="0"
          max="1"
          step="0.01"
          value={formValues.temperature}
          onChange={handleChange}
          style={inputStyle}
          placeholder="0.2"
        />
      </label>

      <label style={{ display: 'block', marginBottom: '0.75rem' }}>
        <span style={{ display: 'block', marginBottom: '0.35rem' }}>Max Tokens</span>
        <input
          name="max_tokens"
          type="number"
          min="1"
          step="1"
          value={formValues.max_tokens}
          onChange={handleChange}
          style={inputStyle}
          placeholder="256"
        />
      </label>

      <label style={{ display: 'block', marginBottom: '1rem' }}>
        <span style={{ display: 'block', marginBottom: '0.35rem' }}>System Prompt</span>
        <textarea
          name="system_prompt"
          rows={6}
          value={formValues.system_prompt}
          onChange={handleChange}
          style={{ ...inputStyle, minHeight: '120px', resize: 'vertical' }}
          placeholder="You are a helpful assistant..."
        />
      </label>

      <div style={{ marginBottom: '0.75rem', padding: '0.75rem', borderRadius: '10px', background: '#17181d' }}>
        <div style={{ fontSize: '0.9rem', color: '#8fa1b2' }}>Payload preview</div>
        <pre style={{ margin: '0.35rem 0 0', whiteSpace: 'pre-wrap', color: '#f5f5f5', fontSize: '0.9rem' }}>
          {settingsPreview ? JSON.stringify(settingsPreview, null, 2) : 'Fix the highlighted values to continue.'}
        </pre>
      </div>

      <button
        type="submit"
        disabled={status === 'loading'}
        style={{
          width: '100%',
          padding: '0.8rem 1rem',
          border: 'none',
          borderRadius: '10px',
          background: status === 'loading' ? '#4d5b6f' : '#2f80ed',
          color: '#fff',
          cursor: status === 'loading' ? 'wait' : 'pointer',
          fontWeight: 600,
        }}
      >
        {status === 'loading' ? 'Saving…' : 'Save Settings'}
      </button>

      {message ? <p style={{ color: '#6ee7b7', marginTop: '0.75rem' }}>{message}</p> : null}
      {error ? <p style={{ color: '#fca5a5', marginTop: '0.75rem' }}>{error}</p> : null}
    </form>
  );
}

const inputStyle = {
  width: '100%',
  boxSizing: 'border-box',
  padding: '0.7rem 0.8rem',
  borderRadius: '10px',
  border: '1px solid #2d3748',
  background: '#111216',
  color: '#f5f5f5',
  fontSize: '0.95rem',
};
