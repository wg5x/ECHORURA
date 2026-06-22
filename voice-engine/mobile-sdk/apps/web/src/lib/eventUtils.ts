import type { VoiceEvent } from "@ai-engine/shared";
import type { CallReport } from "../app/types";

export function formatVoiceEventText(text: string) {
  return collapseRepeatedText(normalizeVoiceEventText(text)) || text;
}

export function mergeVoiceEventText(previous: VoiceEvent, next: VoiceEvent) {
  const previousText = normalizeVoiceEventText(previous.text);
  const nextText = normalizeVoiceEventText(next.text);

  if (!previousText) return next.text;
  if (!nextText) return previous.text;
  const compactPreviousText = compactForRepeatCheck(previousText);
  const compactNextText = compactForRepeatCheck(nextText);
  if (nextText === previousText || previousText.endsWith(nextText)) return formatEventText(next.type, previousText);
  if (nextText.endsWith(previousText) || nextText.includes(previousText)) return formatEventText(next.type, nextText);
  if (previousText.includes(nextText)) return formatEventText(next.type, previousText);
  if (compactNextText && compactPreviousText && compactNextText.includes(compactPreviousText)) return formatEventText(next.type, nextText);
  if (compactPreviousText && compactNextText && compactPreviousText.includes(compactNextText)) return formatEventText(next.type, previousText);
  if (previous.type === "assistant" && next.type === "assistant" && isLikelyAssistantCorrection(compactPreviousText, compactNextText)) {
    return formatEventText(next.type, nextText);
  }
  if (previousText === stripAssistantStatusPrefix(nextText)) return previous.text;
  if (stripAssistantStatusPrefix(previousText) === nextText) return formatEventText(next.type, nextText);

  const mergedText = nextText.startsWith(previousText) ? nextText : appendWithOverlap(previousText, nextText);
  return `${getVoiceEventPrefix(next.type)}${collapseRepeatedText(mergedText)}`;
}

export function toElapsedMs(start: number, end?: number) {
  return end === undefined ? undefined : Math.max(0, Math.round(end - start));
}

export function buildBasicSummary(transcript: CallReport["transcript"]) {
  if (!transcript.length) {
    return "本次会话尚未形成有效转写。";
  }

  const userTurns = transcript.filter((item) => item.role === "user");
  const assistantTurns = transcript.filter((item) => item.role === "assistant");
  const latestUser = userTurns[userTurns.length - 1]?.text;
  const latestAssistant = assistantTurns[assistantTurns.length - 1]?.text;
  if (latestUser && latestAssistant) {
    return `基础摘要：用户最近提到“${latestUser.slice(0, 48)}”，助手回应“${latestAssistant.slice(0, 48)}”。`;
  }
  if (latestUser) return `基础摘要：用户最近提到“${latestUser.slice(0, 64)}”。`;
  return `基础摘要：助手最近回应“${latestAssistant?.slice(0, 64) ?? ""}”。`;
}

function getVoiceEventPrefix(type: VoiceEvent["type"]) {
  if (type === "asr") return "ASRResponse: ";
  if (type === "assistant") return "ChatResponse: ";
  return "";
}

function formatEventText(type: VoiceEvent["type"], text: string) {
  return `${getVoiceEventPrefix(type)}${collapseRepeatedText(text)}`;
}

function isLikelyAssistantCorrection(previousText: string, nextText: string) {
  if (previousText.length < 8 || nextText.length < 8) return false;
  const sharedLength = sharedPrefixLength(previousText, nextText) + sharedSuffixLength(previousText, nextText);
  return sharedLength / Math.min(previousText.length, nextText.length) >= 0.86;
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

function normalizeVoiceEventText(text: string) {
  return stripAssistantStatusPrefix(
    normalizeInvisibleSpaces(text)
      .replace(/^(ASRResponse|ChatResponse|SessionStarted|SessionFinished):\s*/, "")
      .trim(),
  );
}

function stripAssistantStatusPrefix(text: string) {
  return text.replace(/^(正在回复|正在演唱)[：:]\s*/, "").trim();
}

function appendWithOverlap(previous: string, next: string) {
  const maxOverlap = Math.min(previous.length, next.length);
  for (let length = maxOverlap; length > 0; length -= 1) {
    if (previous.endsWith(next.slice(0, length))) {
      return `${previous}${next.slice(length)}`;
    }
  }
  return `${previous}${next}`;
}

function collapseRepeatedText(text: string) {
  let current = collapseVisualRepeatedText(normalizeInvisibleSpaces(text.trim()));
  current = collapseAdjacentRepeatedChunks(current);
  let changed = true;

  while (changed) {
    changed = false;
    const maxLength = Math.floor(current.length / 2);
    for (let length = maxLength; length > 0; length -= 1) {
      const repeated = current.slice(0, length);
      const rest = current.slice(length);
      if (repeated && rest.startsWith(repeated)) {
        current = collapseAdjacentRepeatedChunks(`${repeated}${rest.slice(length)}`.trim());
        changed = true;
        break;
      }
    }
  }

  return current;
}

function collapseVisualRepeatedText(text: string) {
  const compact = compactForRepeatCheck(text);
  if (!compact || compact.length % 2 !== 0) return text;

  const halfLength = compact.length / 2;
  if (compact.slice(0, halfLength) !== compact.slice(halfLength)) return text;

  let seen = 0;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index] ?? "";
    if (/[\p{L}\p{N}]/u.test(char)) {
      seen += 1;
      if (seen === halfLength) {
        return text.slice(0, index + 1).trim();
      }
    }
  }
  return text;
}

function collapseAdjacentRepeatedChunks(text: string) {
  let current = text.trim();
  let changed = true;
  while (changed) {
    const next = current
      .replace(/([\p{L}\p{N}]{2,})([，,。！？!?、；;\s]*)\1/gu, "$1")
      .replace(/([\p{L}\p{N}]{2,})([，,。！？!?、；;\s]*(?:噢|哦|啊|呀|呃|嗯|额|哈)[，,。！？!?、；;\s]*)\1/gu, "$1")
      .trim();
    changed = next !== current;
    current = next;
  }
  return current;
}

function compactForRepeatCheck(text: string) {
  return normalizeInvisibleSpaces(text).replace(/[^\p{L}\p{N}]/gu, "");
}

function normalizeInvisibleSpaces(text: string) {
  return text.replace(/[\u200b\ufeff]/g, "").replace(/\u00a0/g, " ");
}
