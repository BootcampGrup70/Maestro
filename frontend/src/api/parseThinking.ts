export interface SplitThinkingResult {
  content: string;
  thinking: string | null;
}

export function splitThinking(content: string | null): SplitThinkingResult {
  if (!content) return { content: "", thinking: null };

  const closeTag = "</think>";
  const closeIdx = content.indexOf(closeTag);
  if (closeIdx === -1) {
    return { content, thinking: null };
  }

  const openTag = "<think>";
  const openIdx = content.indexOf(openTag);
  const thinking =
    openIdx !== -1 && openIdx < closeIdx
      ? content.slice(openIdx + openTag.length, closeIdx).trim()
      : content.slice(0, closeIdx).trim();

  const rest = content.slice(closeIdx + closeTag.length).trim();
  return { content: rest, thinking: thinking || null };
}
