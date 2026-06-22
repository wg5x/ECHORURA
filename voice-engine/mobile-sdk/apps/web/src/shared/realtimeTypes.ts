export type CallStatus = "idle" | "connecting" | "connected" | "ending";
export type ModelMode = "o2" | "sc2";
export type WebSearchType = "web" | "web_summary" | "web_agent";

export type VoiceEvent = {
  id: string;
  outputId?: string;
  type: "asr" | "assistant" | "system";
  text: string;
  at: string;
};

export type RealtimeConfig = {
  mode: ModelMode;
  speaker: string;
  podcastHostA?: string;
  podcastHostB?: string;
  podcastStyle?: string;
  botName: string;
  systemRole: string;
  speakingStyle: string;
  characterManifest: string;
  interviewOutline: string;
  openingLine: string;
  strictAudit: boolean;
  enableWebSearch: boolean;
  webSearchType: WebSearchType;
  webSearchResultCount: number;
  webSearchNoResultMessage: string;
  webSearchBotId: string;
  enableMusic: boolean;
  enableLoudnessNorm: boolean;
  enableConversationTruncate: boolean;
  enableUserQueryExit: boolean;
  enableBargeIn: boolean;
  speechRate: number;
  loudnessRate: number;
  explicitDialect: "" | "dongbei" | "sichuan" | "shaanxi";
};
