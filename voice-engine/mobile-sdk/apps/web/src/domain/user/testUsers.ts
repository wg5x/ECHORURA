import { voiceSceneTemplates, type SceneTemplate } from "../scene/sceneTemplates";

export type TestUserProfile = {
  id: string;
  name: string;
  segment: string;
  role: string;
  ageBand: "adult" | "elder" | "minor";
  traits: string[];
  constraints: string[];
  assignedSceneIds: SceneTemplate["id"][];
};

export const testUserProfiles: TestUserProfile[] = [
  {
    id: "admin_operator",
    name: "运营管理员样本",
    segment: "场景管理 / 体验调整",
    role: "admin",
    ageBand: "adult",
    traits: ["负责创建和调整场景", "可以体验全部默认场景", "用于验证后台管理视角"],
    constraints: ["不能绕过音色授权", "不能绕过安全策略"],
    assignedSceneIds: [
      "podcast_creator_duo",
      "podcast_analysis_duo",
      "evening_reflection",
      "language_practice",
      "elder_checkin",
      "hs6_user_interview",
    ],
  },
  {
    id: "podcast_creator_user",
    name: "语音播客创作用户",
    segment: "播客 / 创作者双人解读",
    role: "user",
    ageBand: "adult",
    traits: ["上传报告或粘贴文本", "固定使用黑猫侦探社咪仔和大壹先生主持人组合"],
    constraints: ["脚本需审核后再生成音频", "不自由切换主持人音色"],
    assignedSceneIds: ["podcast_creator_duo"],
  },
  {
    id: "voice_experience_user",
    name: "音色场景体验用户",
    segment: "音色体验 / 20 个角色场景",
    role: "user",
    ageBand: "adult",
    traits: ["从首页选择音色角色场景", "用于快速体验不同 O2/SC2 音色"],
    constraints: ["不能修改场景底层配置", "遵守各音色场景的安全边界"],
    assignedSceneIds: voiceSceneTemplates.map((scene) => scene.id),
  },
  {
    id: "podcast_analysis_user",
    name: "语音播客分析用户",
    segment: "播客 / 分析访谈解读",
    role: "user",
    ageBand: "adult",
    traits: ["上传报告或粘贴文本", "固定使用刘飞和潇磊主持人组合"],
    constraints: ["脚本需审核后再生成音频", "不自由切换主持人音色"],
    assignedSceneIds: ["podcast_analysis_duo"],
  },
  {
    id: "evening_reflection_user",
    name: "晚间复盘用户",
    segment: "默认用户 / 晚间复盘",
    role: "user",
    ageBand: "adult",
    traits: ["晚上容易复盘工作", "希望被倾听", "不喜欢强建议"],
    constraints: ["不做心理治疗承诺", "不诱导长时间依赖"],
    assignedSceneIds: ["evening_reflection"],
  },
  {
    id: "language_practice_user",
    name: "口语陪练用户",
    segment: "默认用户 / 口语陪练",
    role: "user",
    ageBand: "adult",
    traits: ["想提升开口频率", "接受轻量纠错", "偏好具体例句"],
    constraints: ["不承诺考试或面试结果", "不过度打断"],
    assignedSceneIds: ["language_practice"],
  },
  {
    id: "elder_checkin_user",
    name: "适老问候用户",
    segment: "默认用户 / 适老问候",
    role: "user",
    ageBand: "elder",
    traits: ["偏好慢语速", "问题需要简单清楚", "可接受喝水休息提醒"],
    constraints: ["不做医疗诊断", "异常表达提示联系家人"],
    assignedSceneIds: ["elder_checkin"],
  },
  {
    id: "hs6_interview_user",
    name: "红旗 HS6 访谈样本",
    segment: "车主 / 半年内购车或置换意向",
    role: "user",
    ageBand: "adult",
    traits: ["正在看新能源 SUV", "可围绕预算、家庭用车、品牌认知展开访谈", "需要被温和追问真实购车动机"],
    constraints: ["不引导用户给出特定答案", "不做销售转化或购车承诺"],
    assignedSceneIds: ["hs6_user_interview"],
  },
];

export function getTestUserProfile(userId: TestUserProfile["id"], profiles = testUserProfiles) {
  return profiles.find((profile) => profile.id === userId) ?? profiles[0] ?? testUserProfiles[0];
}
