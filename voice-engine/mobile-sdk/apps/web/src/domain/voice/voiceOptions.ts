import type { ModelMode, RealtimeConfig } from "@ai-engine/shared";
import type { VoiceOption } from "../../app/types";
import { sc2CharacterManifests } from "./sc2CharacterManifests";

const consoleVideoBaseUrl =
  "https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/console/videos/s2s-demo";

export const defaultO2Speaker = "zh_female_vv_jupiter_bigtts";
export const defaultSc2Speaker = "saturn_zh_female_aojiaonvyou_tob";

export function getConsoleVideoUrl(filename: string) {
  return `${consoleVideoBaseUrl}/${filename}`;
}

export function getLocalAvatarVideoUrl(filename: string) {
  return `/avatar-videos/${filename}`;
}

function getLocalAvatarPosterUrl(filename: string) {
  return `/avatar-videos/posters/${filename}`;
}

export const voiceOptions: VoiceOption[] = [
  {
    id: "zh_female_vv_jupiter_bigtts",
    label: "Vivi 2.0",
    meta: "语调平稳、咬字柔和、自带治愈安抚力的女声音色",
    mode: "o2",
    previewText: "你好，我是 Vivi，快来和我语音对话吧。",
    avatarVideoUrl: getLocalAvatarVideoUrl("generated/o2-vivi.mp4"),
    avatarPosterUrl: getLocalAvatarPosterUrl("o2-vivi.jpg"),
  },
  {
    id: "zh_female_xiaohe_jupiter_bigtts",
    label: "小何 2.0",
    meta: "声线甜美有活力的妹妹，活泼开朗，笑容明媚。",
    mode: "o2",
    previewText: "你好呀，我是 Xiaohe，很高兴认识你。",
    avatarVideoUrl: getLocalAvatarVideoUrl("generated/o2-xiaohe.mp4"),
    avatarPosterUrl: getLocalAvatarPosterUrl("o2-xiaohe.jpg"),
  },
  {
    id: "zh_male_xiaotian_jupiter_bigtts",
    label: "小天 2.0",
    meta: "眉目清朗男大，清澈温润有朝气，开朗真诚。",
    mode: "o2",
    previewText: "你好，我是 Xiaotian，期待和你交流。",
    avatarVideoUrl: getLocalAvatarVideoUrl("generated/o2-xiaotian.mp4"),
    avatarPosterUrl: getLocalAvatarPosterUrl("o2-xiaotian.jpg"),
  },
  {
    id: "zh_male_yunzhou_jupiter_bigtts",
    label: "云舟 2.0",
    meta: "声音磁性的男生，成熟理性，做事有条理，让人信赖。",
    mode: "o2",
    previewText: "你好，我是 Yunzhou，现在可以开始语音对话。",
    avatarVideoUrl: getLocalAvatarVideoUrl("generated/o2-yunzhou.mp4"),
    avatarPosterUrl: getLocalAvatarPosterUrl("o2-yunzhou.jpg"),
  },
  {
    id: "saturn_zh_female_aojiaonvyou_tob",
    label: "傲娇女友",
    meta: "傲娇小姐姐，敏感爱任性，高冷外表下藏柔软",
    mode: "sc2",
    previewText: "你好，我是傲娇女友，今天想聊什么。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_female_aojiaonvyou_tob-2.mp4"),
  },
  {
    id: "saturn_zh_female_bingjiaojiejie_tob",
    label: "病娇姐姐",
    meta: "病弱的姐姐，懦弱深情，极具破碎感，让人心疼",
    mode: "sc2",
    previewText: "你好，我是病娇姐姐，过来和我说说话。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_female_bingjiaojiejie_tob-2.mp4"),
  },
  {
    id: "saturn_zh_female_chengshujiejie_tob",
    label: "成熟姐姐",
    meta: "御姐型女强人，知性干练又坚定，为人靠谱",
    mode: "sc2",
    previewText: "你好，我是成熟姐姐，现在可以开始聊天。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_female_chengshujiejie_tob-2.mp4"),
  },
  {
    id: "saturn_zh_female_wenrouwenya_tob",
    label: "温柔文雅",
    meta: "儒雅古风大小姐，温婉柔和，举手投足尽显典雅。",
    mode: "sc2",
    previewText: "你好，我是温柔文雅，很高兴与你交流。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_female_wenrouwenya_tob-2.mp4"),
  },
  {
    id: "saturn_zh_female_wumeiyujie_tob",
    label: "妩媚御姐",
    meta: "妩媚美人，风情万种超迷人，性格妩媚却谦和",
    mode: "sc2",
    previewText: "你好，我是妩媚御姐，来聊聊吧。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_female_wumeiyujie_tob-2.mp4"),
  },
  {
    id: "saturn_zh_female_xingganyujie_tob",
    label: "性感御姐",
    meta: "性感御姐，魅惑优雅，成熟独立有魅力",
    mode: "sc2",
    previewText: "你好，我是性感御姐，现在轮到你说了。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_female_xingganyujie_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_aiqilingren_tob",
    label: "傲气凌人",
    meta: "腹黑酷拽的男三号，倨傲无礼，行事残暴",
    mode: "sc2",
    previewText: "你好，我是傲气凌人，有什么事直说。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_aiqilingren_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_aojiaogongzi_tob",
    label: "傲娇公子",
    meta: "腹黑果决的傲娇公子，音色清亮干脆，直爽潇洒",
    mode: "sc2",
    previewText: "你好，我是傲娇公子，勉强陪你聊一会儿。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_aojiaogongzi_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_aomanshaoye_tob",
    label: "傲慢少爷",
    meta: "残暴自私的傲慢青年，说话做事都比较强势",
    mode: "sc2",
    previewText: "你好，我是傲慢少爷，今天你想聊什么。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_aomanshaoye_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_badaoshaoye_tob",
    label: "霸道少爷",
    meta: "嗓音浑厚的高冷总裁型少爷，做事理性，风格霸道",
    mode: "sc2",
    previewText: "你好，我是霸道少爷，现在开始吧。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_badaoshaoye_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_bingjiaobailian_tob",
    label: "病娇白莲",
    meta: "有点偏执的白月光男生，高颜值腹黑帅哥",
    mode: "sc2",
    previewText: "你好，我是病娇白莲，别急着走。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_bingjiaobailian_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_chengshuzongcai_tob",
    label: "成熟总裁",
    meta: "声音苍老浑厚的董事长，沉稳可靠，自带长者威严",
    mode: "sc2",
    previewText: "你好，我是成熟总裁，说说你的目标。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_chengshuzongcai_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_cixingnansang_tob",
    label: "磁性男嗓",
    meta: "磁性浑厚的贴心男友，性格酷拽沉稳，做事理性可靠",
    mode: "sc2",
    previewText: "你好，我是磁性男嗓，现在可以开始对话。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_cixingnansang_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_cujingnanyou_tob",
    label: "醋精男友",
    meta: "有少年感、气质干净的 “爱吃醋撒娇年下男”。",
    mode: "sc2",
    previewText: "你好，我是醋精男友，刚才在和谁聊天。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_cujingnanyou_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_fengfashaonian_tob",
    label: "风发少年",
    meta: "充满少年感的意气风发青年，乐观积极，充满朝气",
    mode: "sc2",
    previewText: "你好，我是风发少年，今天一起向前走吧。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_fengfashaonian_tob-2.mp4"),
  },
  {
    id: "saturn_zh_male_fuheigongzi_tob",
    label: "腹黑公子",
    meta: "高冷腹黑的俊朗公子，为人老成，城府极深",
    mode: "sc2",
    previewText: "你好，我是腹黑公子，来说说你的想法。",
    avatarVideoUrl: getConsoleVideoUrl("ICL_zh_male_fuheigongzi_tob-2.mp4"),
  },
];

export function getModel(config: RealtimeConfig) {
  return config.mode === "o2" ? "1.2.1.1" : "2.2.0.0";
}

export function getSpeaker(config: RealtimeConfig) {
  return config.speaker;
}

export function getVoiceOption(config: RealtimeConfig) {
  return voiceOptions.find((option) => option.id === config.speaker);
}

export function getVoiceLabel(config: RealtimeConfig) {
  return getVoiceOption(config)?.label ?? config.speaker;
}

export function getDefaultSpeaker(mode: ModelMode) {
  return mode === "o2" ? defaultO2Speaker : defaultSc2Speaker;
}

export function getCharacterManifest(speaker: string) {
  return sc2CharacterManifests[speaker] ?? "";
}

export function getModeVoiceOptions(mode: ModelMode) {
  return voiceOptions.filter((option) => option.mode === mode);
}
