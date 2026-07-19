import test from 'node:test';
import assert from 'node:assert/strict';
import { buildAgentSettingsPayload } from './agentSettingsUtils.js';

test('buildAgentSettingsPayload validates values and maps max_tokens to num_predict', () => {
  const payload = buildAgentSettingsPayload({
    temperature: '0.4',
    max_tokens: '256',
    system_prompt: 'You are helpful.',
    unknown: 'ignore me',
  });

  assert.deepEqual(payload, {
    system_prompt: 'You are helpful.',
    settings: {
      temperature: 0.4,
      num_predict: 256,
    },
  });
});

test('buildAgentSettingsPayload rejects invalid temperature and max_tokens values', () => {
  assert.throws(() => buildAgentSettingsPayload({ temperature: '1.2' }), /temperature/i);
  assert.throws(() => buildAgentSettingsPayload({ max_tokens: '0' }), /max_tokens/i);
  assert.throws(() => buildAgentSettingsPayload({ max_tokens: 'abc' }), /max_tokens/i);
});
