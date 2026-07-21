export interface AgentSettingsFormValues {
  temperature?: string;
  max_tokens?: string;
  system_prompt?: string;
}

export interface AgentSettingsPayload {
  system_prompt?: string;
  settings?: {
    temperature?: number;
    num_predict?: number;
  };
}

export function buildAgentSettingsPayload(values: AgentSettingsFormValues): AgentSettingsPayload {
  const payload: AgentSettingsPayload = {};
  const settings: NonNullable<AgentSettingsPayload["settings"]> = {};

  if (values.system_prompt !== undefined && values.system_prompt !== null) {
    payload.system_prompt = String(values.system_prompt).trim();
  }

  if (values.temperature !== undefined && values.temperature !== null && values.temperature !== "") {
    const temperature = Number(values.temperature);
    if (!Number.isFinite(temperature) || temperature < 0 || temperature > 1) {
      throw new Error("temperature must be a number between 0 and 1");
    }
    settings.temperature = temperature;
  }

  if (values.max_tokens !== undefined && values.max_tokens !== null && values.max_tokens !== "") {
    const maxTokens = Number(values.max_tokens);
    if (!Number.isInteger(maxTokens) || maxTokens <= 0) {
      throw new Error("max_tokens must be a positive integer");
    }
    settings.num_predict = maxTokens;
  }

  if (Object.keys(settings).length > 0) {
    payload.settings = settings;
  }

  return payload;
}
