export type SafetyPolicy = {
  id: string;
  title: string;
  intent: string;
  rules: string[];
  escalation: string[];
};

export type MemoryPolicy = {
  id: string;
  title: string;
  mode: "off" | "review_only" | "auto" | "local_compressed";
  rules: string[];
};

export type ReportPolicy = {
  id: string;
  title: string;
  sections: string[];
  metrics: string[];
};

export const safetyPolicies: Record<string, SafetyPolicy> = {
  daily_companion_safe_v1: {
    id: "daily_companion_safe_v1",
    title: "日常陪伴安全策略",
    intent: "允许温和倾听和轻量复盘，避免心理治疗、依赖诱导和高风险承诺。",
    rules: [
      "明确 AI 身份，不伪装真人或专业咨询师。",
      "不做心理诊断、医疗建议、法律或金融结论。",
      "少建议、多确认，避免制造情感依赖。",
      "成人、擦边、未成年人恋爱陪伴内容默认拒绝。",
    ],
    escalation: ["自伤/他伤/严重危机表达时停止角色化陪伴。", "提示联系可信任的人、当地紧急服务或专业机构。"],
  },
  learning_safe_v1: {
    id: "learning_safe_v1",
    title: "学习陪练安全策略",
    intent: "鼓励表达练习，但不制造考试焦虑或虚假能力承诺。",
    rules: [
      "纠错轻量具体，不频繁打断用户。",
      "不承诺考试结果或职业结果。",
      "未成年人默认使用更克制的表达和内容范围。",
      "拒绝成人、暴力或隐私诱导话题。",
    ],
    escalation: ["用户明显焦虑或崩溃时转为安抚和暂停建议。", "涉及危险行为时提示联系监护人或可信任的人。"],
  },
  elder_checkin_safe_v1: {
    id: "elder_checkin_safe_v1",
    title: "适老问候安全策略",
    intent: "支持日常问候、闲聊和轻提醒，不替代医疗照护或紧急救援。",
    rules: [
      "语速慢、句子短，每次只问一个问题。",
      "用药只按既有安排做提醒，不判断药量或病情。",
      "不提供医疗诊断、治疗建议或安全救援承诺。",
      "不诱导消费，不制造陪伴依赖。",
      "敏感身份、住址、健康信息默认不进入长期记忆。",
    ],
    escalation: ["身体明显不适、迷路、摔倒、求助等表达要提示联系家人或社区。", "紧急风险时提示联系当地紧急服务。"],
  },
  research_interview_safe_v1: {
    id: "research_interview_safe_v1",
    title: "用户研究访谈安全策略",
    intent: "支持中立访谈、样本甄别和需求挖掘，避免销售诱导、隐私采集和结论性建议。",
    rules: [
      "明确访谈目的，保持中立，不暗示标准答案。",
      "一次只问一个问题，用户回答含糊时追问具体例子或原因。",
      "不做购车建议、金融方案、价格承诺或产品保证。",
      "不收集身份证、手机号、详细住址、车牌号等敏感信息。",
      "样本不符合条件时礼貌结束，不继续深入追问。",
    ],
    escalation: ["用户拒访或明显不适时停止访谈。", "涉及敏感个人信息时提醒无需提供，并回到非敏感问题。"],
  },
};

export const memoryPolicies: Record<string, MemoryPolicy> = {
  local_compressed_memory_v1: {
    id: "local_compressed_memory_v1",
    title: "本地压缩记忆",
    mode: "local_compressed",
    rules: [
      "会后把本次转写压缩成一张短记忆卡，下一次通话按开关注入。",
      "当前落地在 openspeech 链路的 system_role / character_manifest，不使用 RTC MemoryConfig。",
      "只注入有长度上限的摘要、偏好和待承接话题，不注入完整历史转写。",
      "敏感个人信息、健康、财务、住址和未成年人画像默认不写入。",
    ],
  },
};

export const reportPolicies: Record<string, ReportPolicy> = {
  reflection_report_v1: {
    id: "reflection_report_v1",
    title: "晚间复盘报告",
    sections: ["今日三件事", "困扰点", "明日轻计划", "风险提示"],
    metrics: ["通话时长", "有效轮次", "Token", "首包延迟", "错误记录"],
  },
  practice_report_v1: {
    id: "practice_report_v1",
    title: "口语陪练报告",
    sections: ["有效轮次", "表达亮点", "可改进表达", "下次练习主题"],
    metrics: ["开口轮次", "助手轮次", "Token", "首包延迟", "错误记录"],
  },
  elder_checkin_report_v1: {
    id: "elder_checkin_report_v1",
    title: "适老问候报告",
    sections: ["接通时长", "近况摘要", "轻提醒", "异常表达"],
    metrics: ["接通时长", "平均响应延迟", "Token", "异常表达数", "错误记录"],
  },
  auto_research_report_v1: {
    id: "auto_research_report_v1",
    title: "汽车用户访谈报告",
    sections: ["样本是否合格", "购车预算与动机", "核心决策因素", "HS6 卖点反馈", "品牌认知与用户画像"],
    metrics: ["访谈时长", "有效轮次", "甄别通过状态", "Token", "错误记录"],
  },
};

export function getSafetyPolicy(policyId: string) {
  return safetyPolicies[policyId];
}

export function getMemoryPolicy(policyId: string) {
  return memoryPolicies[policyId];
}

export function getReportPolicy(policyId: string) {
  return reportPolicies[policyId];
}
