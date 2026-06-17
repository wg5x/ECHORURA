export type VoiceSessionConfig = {
  mode: "o2" | "sc2";
  botName: string;
  speaker: string;
  systemRole: string;
  speakingStyle: string;
  openingLine: string;
  enableWebSearch: boolean;
  enableMusic: boolean;
};

export type VoiceProfile = {
  id: string;
  name: string;
  config: VoiceSessionConfig;
};

export const DEFAULT_VOICE_PROFILE: VoiceProfile = {
  id: "echorura-default",
  name: "ECHORURA 默认语音",
  config: {
    mode: "o2",
    botName: "ECHORURA",
    speaker: "zh_female_vv_jupiter_bigtts",
    systemRole: "你是 ECHORURA 的语音入口助手。先用简短中文自然对话，支持唱歌请求和联网搜索。",
    speakingStyle: "表达自然、简短、友好。优先一句话回答。",
    openingLine: "你好，我是 ECHORURA。你可以和我语音对话，也可以让我唱歌或联网搜索。",
    enableWebSearch: true,
    enableMusic: true
  }
};
