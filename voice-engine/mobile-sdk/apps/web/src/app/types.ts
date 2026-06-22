import type { CallStatus, ModelMode, VoiceEvent } from "@ai-engine/shared";
import type { SceneTemplate } from "../domain/scene/sceneTemplates";
import type { TestUserProfile } from "../domain/user/testUsers";

export type ServerMessage =
  | {
      type: "status";
      status: CallStatus;
      mode?: "volcengine";
      warnings?: string[];
      sessionId?: string;
      requestId?: string;
    }
  | { type: "event"; event: VoiceEvent }
  | { type: "interrupt_ack"; targetOutputId?: string }
  | { type: "usage"; tokens: number }
  | {
      type: "payload";
      payload: unknown;
      warnings?: string[];
      mode: "volcengine";
    }
  | { type: "audio"; data: string; mime: string; outputId?: string }
  | { type: "error"; message: string; payload?: unknown; warnings?: string[] };

export type PayloadPreview = {
  payload: unknown;
  warnings?: string[];
  mode?: "volcengine";
};

export type VoicePreviewResponse = {
  data?: string;
  error?: string;
  mime?: string;
  warnings?: string[];
};

export type MemoryCard = {
  version: "local-memory-card-v1";
  userId: string;
  sceneId: string;
  updatedAt: string | null;
  maxChars: number;
  facts: string[];
  profile: string[];
  preferences: string[];
  conversationStyle: string[];
  openThreads: string[];
  doNotAssume: string[];
  lastSessionSummary: string;
};

export type MemoryCardResponse = {
  card: MemoryCard | null;
  found?: boolean;
  error?: string;
};

export type MemoryCompressResponse = {
  card?: MemoryCard;
  source?: string;
  warnings?: string[];
  error?: string;
};

export type MemoryStatus = "idle" | "loading" | "empty" | "ready" | "compressing" | "saved" | "clearing" | "error";

export type IntentResult = {
  version: "local-intent-v1";
  intent:
    | "unknown"
    | "high_risk"
    | "exit_session"
    | "podcast_request"
    | "memory_update"
    | "profile_question"
    | "scene_change"
    | "ad_opportunity"
    | "general_chat";
  confidence: number;
  reasons: string[];
  actions: string[];
  observedText: string;
};

export type PodcastDraftRound = {
  idx: number;
  speaker: string;
  text: string;
};

export type PodcastDraft = {
  version: "local-podcast-draft-v1";
  title: string;
  format: "duo_brief";
  durationMinutes: number;
  sourceSummary: string;
  rounds: PodcastDraftRound[];
  synthesis: {
    provider: "volc_podcast";
    recommendedAction: number;
    maxRoundChars: number;
    readyForReview: boolean;
  };
  warnings: string[];
};

export type PodcastAudioResult = {
  version: "volc-podcast-audio-v1";
  status: "ready" | "needs_config" | "not_implemented";
  audioUrl: string | null;
  payload: unknown;
  warnings: string[];
};

export type UserProfile = {
  version: "local-user-profile-v1";
  userId: string;
  sceneId: string | null;
  updatedAt: string | null;
  stableFacts: string[];
  profile: string[];
  preferences: string[];
  conversationStyle: string[];
  openThreads: string[];
  boundaries: string[];
  evidence: Array<{ sceneId?: string; updatedAt?: string | null }>;
  warnings: string[];
};

export type VoiceOption = {
  id: string;
  label: string;
  meta: string;
  mode: ModelMode;
  previewText: string;
  avatarVideoUrl?: string;
  avatarPosterUrl?: string;
};

export type RuntimeRole = {
  id: string;
  name: string;
  description: string;
  builtIn?: boolean;
  createdAt?: string | null;
  createdBy?: string | null;
};

export type CreateUserInput = {
  id: string;
  name: string;
  segment: string;
  role: string;
  ageBand: TestUserProfile["ageBand"];
  traits: string[];
  constraints: string[];
  assignedSceneIds: string[];
};

export type CreateRoleInput = {
  id: string;
  name: string;
  description: string;
};

export type CreateSceneInput = {
  id: string;
  sceneKind: "dialogue" | "podcast";
  mode: ModelMode;
  speaker: string;
  botName: string;
  title: string;
  subtitle: string;
  audience: string;
  conversationGuide: string;
  interviewOutline: string;
  openingLine: string;
  systemRole: string;
  speakingStyle: string;
  characterManifest: string;
  podcastHostA: string;
  podcastHostB: string;
  podcastStyle: string;
};

export type CreateSceneResult = {
  scene: SceneTemplate;
  user: TestUserProfile;
};

export type RuntimeMetrics = {
  connectStartedAt: number;
  wsOpenedAt?: number;
  connectedAt?: number;
  firstAsrAt?: number;
  firstAssistantAt?: number;
  firstAudioAt?: number;
  firstPlaybackScheduledAt?: number;
  playbackReadyAt?: number;
  errors: string[];
};

export type CallReport = {
  id: string;
  sceneTitle: string;
  sceneVersion: string;
  userName: string;
  userSegment: string;
  modelProfileId: string;
  safetyPolicy: string;
  memoryPolicy: string;
  reportPolicy: string;
  reportFocus: string[];
  startedAt: string;
  endedAt: string;
  durationSeconds: number;
  tokens: number | null;
  userTurns: number;
  assistantTurns: number;
  transcript: Array<{ role: "user" | "assistant"; text: string; at: string }>;
  summary: string;
  metrics: {
    wsOpenMs?: number;
    startSessionMs?: number;
    firstAsrMs?: number;
    firstAssistantMs?: number;
    firstAudioMs?: number;
    firstPlaybackScheduledMs?: number;
    playbackReadyMs?: number;
    errors: string[];
  };
};

export type CallLogEntry = {
  id: string;
  requestId?: string | null;
  sessionId?: string | null;
  userId: string;
  sceneId: string;
  savedAt: string;
  report: CallReport;
};
