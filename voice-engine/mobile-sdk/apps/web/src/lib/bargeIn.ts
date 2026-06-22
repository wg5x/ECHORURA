export type BargeInState = "idle" | "assistant_speaking" | "user_speech_candidate" | "interrupted" | "recovering";

export type BargeInSnapshot = {
  recentSpeechCandidateAt: number | null;
  speechFrames: number;
  state: BargeInState;
};

export type BargeInConfig = {
  candidateWindowMs: number;
  consecutiveFrames: number;
  peakThreshold: number;
  rmsThreshold: number;
};

export const defaultBargeInConfig: BargeInConfig = {
  candidateWindowMs: 2500,
  consecutiveFrames: 2,
  peakThreshold: 0.08,
  rmsThreshold: 0.024,
};

const shortInterruptUtterances = new Set([
  "停",
  "暂停",
  "停下",
  "停一下",
  "等下",
  "等一下",
  "等等",
  "别说",
  "别说了",
  "不要说了",
  "先停",
  "打断",
  "打断一下",
  "不对",
  "不是",
  "stop",
  "pause",
  "wait",
  "holdon",
]);

export function createBargeInSnapshot(): BargeInSnapshot {
  return {
    recentSpeechCandidateAt: null,
    speechFrames: 0,
    state: "idle",
  };
}

export function resetBargeInSnapshot(): BargeInSnapshot {
  return createBargeInSnapshot();
}

export function markBargeInInterrupted(snapshot: BargeInSnapshot): BargeInSnapshot {
  return {
    ...snapshot,
    recentSpeechCandidateAt: null,
    speechFrames: 0,
    state: "interrupted",
  };
}

export function markBargeInRecovering(snapshot: BargeInSnapshot): BargeInSnapshot {
  return {
    ...snapshot,
    recentSpeechCandidateAt: null,
    speechFrames: 0,
    state: "recovering",
  };
}

export function observeBargeInAudio(
  input: Float32Array,
  assistantOutputActive: boolean,
  snapshot: BargeInSnapshot,
  nowMs: number,
  config: BargeInConfig = defaultBargeInConfig,
): BargeInSnapshot {
  if (!assistantOutputActive) {
    return {
      recentSpeechCandidateAt: null,
      speechFrames: 0,
      state: snapshot.state === "interrupted" ? "interrupted" : "idle",
    };
  }

  if (!detectVoiceActivity(input, config)) {
    return {
      recentSpeechCandidateAt: snapshot.recentSpeechCandidateAt,
      speechFrames: 0,
      state: "assistant_speaking",
    };
  }

  const speechFrames = snapshot.speechFrames + 1;
  return {
    recentSpeechCandidateAt:
      speechFrames >= config.consecutiveFrames ? nowMs : snapshot.recentSpeechCandidateAt,
    speechFrames,
    state: speechFrames >= config.consecutiveFrames ? "user_speech_candidate" : "assistant_speaking",
  };
}

export function shouldConfirmBargeInFromAsr(
  asrText: string,
  assistantText: string,
  recentSpeechCandidateAt: number | null,
  nowMs: number,
  config: BargeInConfig = defaultBargeInConfig,
) {
  const text = normalizeInterruptText(asrText);
  if (!text) return false;
  if (shortInterruptUtterances.has(text)) return true;
  if (isBackchannelOnly(text) || text.length < 2) return false;
  if (isLikelyAssistantEcho(text, normalizeInterruptText(assistantText))) return false;
  if (text.length >= 8) return true;
  return recentSpeechCandidateAt !== null && nowMs - recentSpeechCandidateAt <= config.candidateWindowMs;
}

function detectVoiceActivity(input: Float32Array, config: BargeInConfig) {
  let sumSquares = 0;
  let peak = 0;
  let voicedSamples = 0;
  const voicedSampleThreshold = config.rmsThreshold * 0.8;
  for (let index = 0; index < input.length; index += 1) {
    const sample = Math.abs(input[index] ?? 0);
    sumSquares += sample * sample;
    if (sample > peak) peak = sample;
    if (sample >= voicedSampleThreshold) voicedSamples += 1;
  }
  const rms = Math.sqrt(sumSquares / Math.max(1, input.length));
  const voicedRatio = voicedSamples / Math.max(1, input.length);
  const hasSpeechLikeDuration = voicedRatio >= 0.08;
  const hasSpeechLikeEnergy = rms >= config.rmsThreshold && peak >= config.peakThreshold * 0.6;
  return hasSpeechLikeDuration && hasSpeechLikeEnergy;
}

function normalizeInterruptText(text: string) {
  return text
    .replace(/^(ASRResponse|ChatResponse):\s*/, "")
    .toLowerCase()
    .replace(/[\s，。！？、,.!?;；:："'“”‘’()[\]{}<>《》【】\-—_~·…]/g, "");
}

function isBackchannelOnly(text: string) {
  return /^(嗯+|啊+|哦+|噢+|呃+|额+|诶+|哎+|唉+|喔+|哈+|好的?|可以|行|好嘞|没问题|明白|知道了)$/.test(text);
}

function isLikelyAssistantEcho(userText: string, assistantText: string) {
  if (!userText || !assistantText || userText.length < 3) return false;
  if (assistantText.includes(userText)) return true;

  const userBigrams = new Set<string>();
  for (let index = 0; index < userText.length - 1; index += 1) {
    userBigrams.add(userText.slice(index, index + 2));
  }
  if (!userBigrams.size) return false;

  let shared = 0;
  userBigrams.forEach((bigram) => {
    if (assistantText.includes(bigram)) shared += 1;
  });
  return shared / userBigrams.size >= 0.72;
}
