import type { VoiceEvent } from "@ai-engine/shared";
import type { CallReport, RuntimeMetrics } from "../../app/types";
import type { SceneTemplate } from "../../domain/scene/sceneTemplates";
import { buildBasicSummary, formatVoiceEventText, mergeVoiceEventText, toElapsedMs } from "../../lib/eventUtils";
import { createClientId } from "../../lib/id";

const DISPLAY_EVENT_LIMIT = 24;

type AppendEventOptions = {
  forceNewTurn?: boolean;
};

export function appendDisplayEvent(current: VoiceEvent[], event: VoiceEvent, options: AppendEventOptions = {}) {
  const latest = current[0];
  if (event.type !== "system" && latest?.type === event.type && canMergeEvents(latest, event, options)) {
    return [
      mergeVoiceEvents(latest, event),
      ...current.slice(1),
    ].slice(0, DISPLAY_EVENT_LIMIT);
  }

  const existingAssistantIndex = findAssistantOutputIndex(current, event);
  if (existingAssistantIndex >= 0) {
    return current
      .map((item, index) => index === existingAssistantIndex ? mergeVoiceEvents(item, event) : item)
      .slice(0, DISPLAY_EVENT_LIMIT);
  }

  return [event, ...current].slice(0, DISPLAY_EVENT_LIMIT);
}

export function appendTranscriptEvent(current: VoiceEvent[], event: VoiceEvent, options: AppendEventOptions = {}) {
  if (event.type === "system") return current;

  const latest = current[current.length - 1];
  if (latest?.type === event.type && canMergeEvents(latest, event, options)) {
    return [
      ...current.slice(0, -1),
      mergeVoiceEvents(latest, event),
    ];
  }

  const existingAssistantIndex = findAssistantOutputIndex(current, event);
  if (existingAssistantIndex >= 0) {
    return current.map((item, index) => index === existingAssistantIndex ? mergeVoiceEvents(item, event) : item);
  }

  return [...current, event];
}

function canMergeEvents(previous: VoiceEvent, next: VoiceEvent, options: AppendEventOptions = {}) {
  if (options.forceNewTurn && !isDuplicateAssistantText(previous, next)) return false;
  if (previous.type !== "assistant" && next.type !== "assistant") return true;
  if (isDuplicateAssistantText(previous, next)) return true;
  if (!options.forceNewTurn && isLikelyAssistantCorrection(previous, next)) return true;
  if (!previous.outputId && !next.outputId) return true;
  return Boolean(previous.outputId && next.outputId && previous.outputId === next.outputId);
}

function findAssistantOutputIndex(current: VoiceEvent[], event: VoiceEvent) {
  if (event.type !== "assistant" || !event.outputId) return -1;
  return current.findIndex((item) => item.type === "assistant" && item.outputId === event.outputId);
}

function mergeVoiceEvents(previous: VoiceEvent, next: VoiceEvent): VoiceEvent {
  return {
    ...previous,
    text: mergeVoiceEventText(previous, next),
    outputId: next.outputId ?? previous.outputId,
  };
}

function isDuplicateAssistantText(previous: VoiceEvent, next: VoiceEvent) {
  if (previous.type !== "assistant" || next.type !== "assistant") return false;
  const previousText = compactAssistantText(previous.text);
  const nextText = compactAssistantText(next.text);
  if (!previousText || !nextText) return false;
  return normalizeAssistantDedupText(previousText) === normalizeAssistantDedupText(nextText);
}

function isLikelyAssistantCorrection(previous: VoiceEvent, next: VoiceEvent) {
  if (previous.type !== "assistant" || next.type !== "assistant") return false;
  const previousText = compactAssistantText(previous.text);
  const nextText = compactAssistantText(next.text);
  const minLength = Math.min(previousText.length, nextText.length);
  if (minLength < 8) return false;
  const sharedLength = sharedPrefixLength(previousText, nextText) + sharedSuffixLength(previousText, nextText);
  const edgeCoverage = sharedLength / minLength;
  if (minLength >= 24) return edgeCoverage >= 0.86;
  return edgeCoverage >= 0.9;
}

function compactAssistantText(text: string) {
  return text
    .replace(/^(ASRResponse|ChatResponse|SessionStarted|SessionFinished):\s*/, "")
    .replace(/[\u200b\ufeff]/g, "")
    .replace(/[^\p{L}\p{N}]/gu, "");
}

function trimTrailingParticles(text: string) {
  return text.replace(/[啊呀呢吧哦噢喔啦哈]+$/u, "");
}

function normalizeAssistantDedupText(text: string) {
  return trimTrailingParticles(text)
    .replace(/感谢您的理解/g, "谢谢您的理解")
    .replace(/的状态/g, "状态");
}

function sharedPrefixLength(left: string, right: string) {
  const limit = Math.min(left.length, right.length);
  for (let index = 0; index < limit; index += 1) {
    if (left[index] !== right[index]) {
      return index;
    }
  }
  return limit;
}

function sharedSuffixLength(left: string, right: string) {
  const prefixLength = sharedPrefixLength(left, right);
  const limit = Math.min(left.length, right.length) - prefixLength;
  for (let offset = 0; offset < limit; offset += 1) {
    if (left[left.length - 1 - offset] !== right[right.length - 1 - offset]) {
      return offset;
    }
  }
  return limit;
}

export function buildCallReport(input: {
  endedAtMs?: number;
  events: VoiceEvent[];
  metrics: RuntimeMetrics;
  scene: SceneTemplate;
  startedAtLabel: string;
  startedAtMs: number;
  tokens: number | null;
  userName: string;
  userSegment: string;
}) {
  const endedAtMs = input.endedAtMs ?? Date.now();
  const transcript = input.events.map((event) => ({
    role: event.type === "asr" ? "user" as const : "assistant" as const,
    text: formatVoiceEventText(event.text),
    at: event.at,
  }));

  return {
    id: createClientId(),
    sceneTitle: input.scene.title,
    sceneVersion: input.scene.version,
    userName: input.userName,
    userSegment: input.userSegment,
    modelProfileId: input.scene.modelProfileId,
    safetyPolicy: input.scene.safetyPolicy,
    memoryPolicy: input.scene.memoryPolicy,
    reportPolicy: input.scene.reportPolicy,
    reportFocus: input.scene.reportFocus,
    startedAt: input.startedAtLabel,
    endedAt: new Date(endedAtMs).toLocaleTimeString("zh-CN", { hour12: false }),
    durationSeconds: Math.max(0, Math.round((endedAtMs - input.startedAtMs) / 1000)),
    tokens: input.tokens,
    userTurns: transcript.filter((item) => item.role === "user").length,
    assistantTurns: transcript.filter((item) => item.role === "assistant").length,
    transcript,
    summary: buildBasicSummary(transcript),
    metrics: {
      wsOpenMs: toElapsedMs(input.metrics.connectStartedAt, input.metrics.wsOpenedAt),
      startSessionMs: toElapsedMs(input.metrics.connectStartedAt, input.metrics.connectedAt),
      firstAsrMs: toElapsedMs(input.metrics.connectStartedAt, input.metrics.firstAsrAt),
      firstAssistantMs: toElapsedMs(input.metrics.connectStartedAt, input.metrics.firstAssistantAt),
      firstAudioMs: toElapsedMs(input.metrics.connectStartedAt, input.metrics.firstAudioAt),
      firstPlaybackScheduledMs: toElapsedMs(input.metrics.connectStartedAt, input.metrics.firstPlaybackScheduledAt),
      playbackReadyMs: toElapsedMs(input.metrics.connectStartedAt, input.metrics.playbackReadyAt),
      errors: input.metrics.errors,
    },
  } satisfies CallReport;
}
