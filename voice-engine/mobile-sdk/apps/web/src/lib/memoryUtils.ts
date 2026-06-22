import type { RealtimeConfig } from "@ai-engine/shared";
import type { MemoryCard } from "../app/types";

export function hasMemoryCardContent(card: MemoryCard | null) {
  return Boolean(
    card &&
      (card.lastSessionSummary ||
        (card.facts?.length ?? 0) ||
        card.profile.length ||
        card.preferences.length ||
        card.conversationStyle.length ||
        card.openThreads.length),
  );
}

export function applyLocalMemory(config: RealtimeConfig, card: MemoryCard | null, enabled: boolean): RealtimeConfig {
  if (!enabled || !card || !hasMemoryCardContent(card)) return config;

  const memoryBlock = ["", "# 本地压缩记忆", renderMemoryCardForPrompt(card)].join("\n");

  if (config.mode === "sc2") {
    return {
      ...config,
      characterManifest: `${config.characterManifest}${memoryBlock}`,
    };
  }

  return {
    ...config,
    systemRole: `${config.systemRole}${memoryBlock}`,
  };
}

export function getMemoryCardPreviewItems(card: MemoryCard | null) {
  if (!card) return [];
  return [card.lastSessionSummary, ...(card.facts ?? []), ...card.preferences, ...card.conversationStyle, ...card.openThreads]
    .filter(Boolean)
    .slice(0, 4);
}

function renderMemoryCardForPrompt(card: MemoryCard) {
  const lines = [
    "以下是本地压缩记忆卡，只作为承接上下文使用；如果不确定，先向用户确认，不要当作确定事实。",
    card.lastSessionSummary ? `最近摘要：${card.lastSessionSummary}` : "",
    ...(card.facts ?? []).map((item) => `稳定事实：${item}`),
    ...card.profile.map((item) => `用户画像：${item}`),
    ...card.preferences.map((item) => `用户偏好：${item}`),
    ...card.conversationStyle.map((item) => `互动方式：${item}`),
    ...card.openThreads.map((item) => `待承接话题：${item}`),
    ...card.doNotAssume.map((item) => `边界：${item}`),
  ];
  return lines.filter(Boolean).join("\n");
}
