export function buildAgentSettingsPayload(values) {
  const normalized = {
    temperature: values?.temperature,
    max_tokens: values?.max_tokens,
    system_prompt: values?.system_prompt,
  };

  const payload = {};

  if (normalized.system_prompt !== undefined && normalized.system_prompt !== null) {
    payload.system_prompt = String(normalized.system_prompt).trim();
  }

  const settings = {};

  if (normalized.temperature !== undefined && normalized.temperature !== null && normalized.temperature !== '') {
    const temperature = Number(normalized.temperature);
    if (!Number.isFinite(temperature) || temperature < 0 || temperature > 1) {
      throw new Error('temperature must be a number between 0 and 1');
    }
    settings.temperature = temperature;
  }

  if (normalized.max_tokens !== undefined && normalized.max_tokens !== null && normalized.max_tokens !== '') {
    const maxTokens = Number(normalized.max_tokens);
    if (!Number.isInteger(maxTokens) || maxTokens <= 0) {
      throw new Error('max_tokens must be a positive integer');
    }
    settings.num_predict = maxTokens;
  }

  if (Object.keys(settings).length > 0) {
    payload.settings = settings;
  }

  return payload;
}
