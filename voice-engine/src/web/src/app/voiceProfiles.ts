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
  description: string;
  config: VoiceSessionConfig;
};

export const DEFAULT_VOICE_PROFILE: VoiceProfile = {
  id: "echorura-default",
  name: "ECHORURA 默认语音",
  description: "自然、简短，保留联网和唱歌能力。",
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

export const VOICE_PROFILES: VoiceProfile[] = [
  DEFAULT_VOICE_PROFILE,
  {
    id: "short-latency",
    name: "短回答测试",
    description: "更短回复，用于测试延迟和连续对话。",
    config: {
      ...DEFAULT_VOICE_PROFILE.config,
      speakingStyle: "表达自然、非常简短。优先半句话到一句话回答，不主动展开。",
      openingLine: "你好，我会用更短的回答陪你测试实时语音。"
    }
  },
  {
    id: "music-test",
    name: "音乐测试",
    description: "偏音乐请求，用于测试唱歌和歌曲相关回复。",
    config: {
      ...DEFAULT_VOICE_PROFILE.config,
      systemRole: "你是 ECHORURA 的音乐语音入口助手。优先理解唱歌、歌曲、风格和情绪相关请求，也可以自然闲聊。",
      speakingStyle: "表达自然、简短，有音乐陪伴感。遇到唱歌或歌曲请求时先确认并直接响应。",
      openingLine: "你好，我是 ECHORURA。你可以让我唱歌，也可以说想听的风格或情绪。"
    }
  }
];

export function findVoiceProfile(profileId: string) {
  return VOICE_PROFILES.find((profile) => profile.id === profileId) ?? DEFAULT_VOICE_PROFILE;
}
