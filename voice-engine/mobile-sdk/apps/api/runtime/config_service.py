from __future__ import annotations

import copy
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import LOCAL_RUNTIME_DIR
from ..integrations.volc.payload import normalize_realtime_config
from ..memory.card_service import read_memory_card, render_memory_card_for_prompt
from ..shared.value_utils import to_bool, to_string_value


RUNTIME_CONFIG_DIR = LOCAL_RUNTIME_DIR / "runtime-config"
SCENE_STORE_PATH = RUNTIME_CONFIG_DIR / "scenes.json"
_SESSION_TOKENS: dict[str, str] = {}

DEFAULT_ROLES: list[dict[str, Any]] = [
    {
        "id": "admin",
        "name": "管理员",
        "description": "可以访问后台，管理用户、角色、场景和场景参数。",
        "builtIn": True,
    },
    {
        "id": "user",
        "name": "用户",
        "description": "只能进入自己被分配的场景。",
        "builtIn": True,
    },
]

BASE_REALTIME_CONFIG: dict[str, Any] = {
    "mode": "o2",
    "speaker": "zh_female_vv_jupiter_bigtts",
    "podcastHostA": "",
    "podcastHostB": "",
    "podcastStyle": "",
    "botName": "豆包",
    "systemRole": "",
    "speakingStyle": "",
    "characterManifest": "",
    "interviewOutline": "",
    "openingLine": "",
    "strictAudit": True,
    "enableWebSearch": False,
    "webSearchType": "web",
    "webSearchResultCount": 5,
    "webSearchNoResultMessage": "我暂时没有查到相关信息。",
    "webSearchBotId": "",
    "enableMusic": False,
    "enableLoudnessNorm": True,
    "enableConversationTruncate": True,
    "enableUserQueryExit": True,
    "enableBargeIn": True,
    "speechRate": 0,
    "loudnessRate": 0,
    "explicitDialect": "",
}

VOICE_OPTIONS: list[dict[str, str]] = [
    {"id": "zh_female_vv_jupiter_bigtts", "label": "Vivi 2.0", "meta": "语调平稳、咬字柔和、自带治愈安抚力的女声音色", "mode": "o2"},
    {"id": "zh_female_xiaohe_jupiter_bigtts", "label": "小何 2.0", "meta": "声线甜美有活力的妹妹，活泼开朗，笑容明媚。", "mode": "o2"},
    {"id": "zh_male_xiaotian_jupiter_bigtts", "label": "小天 2.0", "meta": "眉目清朗男大，清澈温润有朝气，开朗真诚。", "mode": "o2"},
    {"id": "zh_male_yunzhou_jupiter_bigtts", "label": "云舟 2.0", "meta": "声音磁性的男生，成熟理性，做事有条理，让人信赖。", "mode": "o2"},
    {"id": "saturn_zh_female_aojiaonvyou_tob", "label": "傲娇女友", "meta": "傲娇小姐姐，敏感爱任性，高冷外表下藏柔软", "mode": "sc2"},
    {"id": "saturn_zh_female_bingjiaojiejie_tob", "label": "病娇姐姐", "meta": "病弱的姐姐，懦弱深情，极具破碎感，让人心疼", "mode": "sc2"},
    {"id": "saturn_zh_female_chengshujiejie_tob", "label": "成熟姐姐", "meta": "御姐型女强人，知性干练又坚定，为人靠谱", "mode": "sc2"},
    {"id": "saturn_zh_female_wenrouwenya_tob", "label": "温柔文雅", "meta": "儒雅古风大小姐，温婉柔和，举手投足尽显典雅。", "mode": "sc2"},
    {"id": "saturn_zh_female_wumeiyujie_tob", "label": "妩媚御姐", "meta": "妩媚美人，风情万种超迷人，性格妩媚却谦和", "mode": "sc2"},
    {"id": "saturn_zh_female_xingganyujie_tob", "label": "性感御姐", "meta": "性感御姐，魅惑优雅，成熟独立有魅力", "mode": "sc2"},
    {"id": "saturn_zh_male_aiqilingren_tob", "label": "傲气凌人", "meta": "腹黑酷拽的男三号，倨傲无礼，行事残暴", "mode": "sc2"},
    {"id": "saturn_zh_male_aojiaogongzi_tob", "label": "傲娇公子", "meta": "腹黑果决的傲娇公子，音色清亮干脆，直爽潇洒", "mode": "sc2"},
    {"id": "saturn_zh_male_aomanshaoye_tob", "label": "傲慢少爷", "meta": "残暴自私的傲慢青年，说话做事都比较强势", "mode": "sc2"},
    {"id": "saturn_zh_male_badaoshaoye_tob", "label": "霸道少爷", "meta": "嗓音浑厚的高冷总裁型少爷，做事理性，风格霸道", "mode": "sc2"},
    {"id": "saturn_zh_male_bingjiaobailian_tob", "label": "病娇白莲", "meta": "有点偏执的白月光男生，高颜值腹黑帅哥", "mode": "sc2"},
    {"id": "saturn_zh_male_chengshuzongcai_tob", "label": "成熟总裁", "meta": "声音苍老浑厚的董事长，沉稳可靠，自带长者威严", "mode": "sc2"},
    {"id": "saturn_zh_male_cixingnansang_tob", "label": "磁性男嗓", "meta": "磁性浑厚的贴心男友，性格酷拽沉稳，做事理性可靠", "mode": "sc2"},
    {"id": "saturn_zh_male_cujingnanyou_tob", "label": "醋精男友", "meta": "有少年感、气质干净的“爱吃醋撒娇年下男”。", "mode": "sc2"},
    {"id": "saturn_zh_male_fengfashaonian_tob", "label": "风发少年", "meta": "充满少年感的意气风发青年，乐观积极，充满朝气", "mode": "sc2"},
    {"id": "saturn_zh_male_fuheigongzi_tob", "label": "腹黑公子", "meta": "高冷腹黑的俊朗公子，为人老成，城府极深", "mode": "sc2"},
]

VOICE_SCENE_IDS = [f"voice_scene_{voice['id']}" for voice in VOICE_OPTIONS]

DEFAULT_USERS: list[dict[str, Any]] = [
    {
        "id": "admin_operator",
        "name": "运营管理员样本",
        "segment": "场景管理 / 体验调整",
        "role": "admin",
        "ageBand": "adult",
        "traits": ["负责创建和调整场景", "可以体验全部默认场景", "用于验证后台管理视角"],
        "constraints": ["不能绕过音色授权", "不能绕过安全策略"],
        "assignedSceneIds": [
            "podcast_creator_duo",
            "podcast_analysis_duo",
            "evening_reflection",
            "language_practice",
            "elder_checkin",
            "hs6_user_interview",
            *VOICE_SCENE_IDS,
        ],
    },
    {
        "id": "podcast_creator_user",
        "name": "语音播客创作用户",
        "segment": "播客 / 创作者双人解读",
        "role": "user",
        "ageBand": "adult",
        "traits": ["上传报告或粘贴文本", "固定使用黑猫侦探社咪仔和大壹先生主持人组合"],
        "constraints": ["脚本需审核后再生成音频", "不自由切换主持人音色"],
        "assignedSceneIds": ["podcast_creator_duo"],
    },
    {
        "id": "voice_experience_user",
        "name": "音色场景体验用户",
        "segment": "音色体验 / 20 个角色场景",
        "role": "user",
        "ageBand": "adult",
        "traits": ["从首页选择音色角色场景", "用于快速体验不同 O2/SC2 音色"],
        "constraints": ["不能修改场景底层配置", "遵守各音色场景的安全边界"],
        "assignedSceneIds": VOICE_SCENE_IDS,
    },
    {
        "id": "podcast_analysis_user",
        "name": "语音播客分析用户",
        "segment": "播客 / 分析访谈解读",
        "role": "user",
        "ageBand": "adult",
        "traits": ["上传报告或粘贴文本", "固定使用刘飞和潇磊主持人组合"],
        "constraints": ["脚本需审核后再生成音频", "不自由切换主持人音色"],
        "assignedSceneIds": ["podcast_analysis_duo"],
    },
    {
        "id": "evening_reflection_user",
        "name": "晚间复盘用户",
        "segment": "默认用户 / 晚间复盘",
        "role": "user",
        "ageBand": "adult",
        "traits": ["晚上容易复盘工作", "希望被倾听", "不喜欢强建议"],
        "constraints": ["不做心理治疗承诺", "不诱导长时间依赖"],
        "assignedSceneIds": ["evening_reflection"],
    },
    {
        "id": "language_practice_user",
        "name": "口语陪练用户",
        "segment": "默认用户 / 口语陪练",
        "role": "user",
        "ageBand": "adult",
        "traits": ["想提升开口频率", "接受轻量纠错", "偏好具体例句"],
        "constraints": ["不承诺考试或面试结果", "不过度打断"],
        "assignedSceneIds": ["language_practice"],
    },
    {
        "id": "elder_checkin_user",
        "name": "适老问候用户",
        "segment": "默认用户 / 适老问候",
        "role": "user",
        "ageBand": "elder",
        "traits": ["偏好慢语速", "问题需要简单清楚", "可接受喝水休息提醒"],
        "constraints": ["不做医疗诊断", "异常表达提示联系家人"],
        "assignedSceneIds": ["elder_checkin"],
    },
    {
        "id": "hs6_interview_user",
        "name": "红旗 HS6 访谈样本",
        "segment": "车主 / 半年内购车或置换意向",
        "role": "user",
        "ageBand": "adult",
        "traits": ["正在看新能源 SUV", "可围绕预算、家庭用车、品牌认知展开访谈", "需要被温和追问真实购车动机"],
        "constraints": ["不引导用户给出特定答案", "不做销售转化或购车承诺"],
        "assignedSceneIds": ["hs6_user_interview"],
    },
]

VOICE_SCENES: list[dict[str, Any]] = [
    {
        "id": f"voice_scene_{voice['id']}",
        "sceneKind": "dialogue",
        "version": "1.0.0",
        "title": f"{voice['label']} 音色体验",
        "subtitle": f"固定使用 {voice['label']}，用于验证单音色用户体验。",
        "audience": f"{voice['label']} 用户",
        "modelProfileId": "volc.doubao.realtime.o2@1.2.1.1" if voice["mode"] == "o2" else "volc.doubao.realtime.sc2@2.2.0.0",
        "requiredCapabilities": ["realtime_voice", "single_voice_profile"],
        "safetyPolicy": "daily_companion_safe_v1",
        "memoryPolicy": "local_compressed_memory_v1",
        "reportPolicy": "reflection_report_v1",
        "conversationGuide": f"这是 {voice['label']} 的专属音色场景。管理员可以基于它调整音色、人设和对话风格。",
        "reportFocus": ["音色体验反馈", "对话自然度", "用户偏好", "风险提示"],
        "config": {
            **BASE_REALTIME_CONFIG,
            "mode": voice["mode"],
            "speaker": voice["id"],
            "botName": f"{voice['label']}助手",
            "systemRole": f"你是一个使用 {voice['label']} 音色的语音助手。保持自然、简洁、友好，不夸大能力，不诱导用户依赖。",
            "speakingStyle": f"{voice['meta']}。回答要口语化、简短、有耐心。",
            "characterManifest": f"你是一个使用 {voice['label']} 音色的角色。{voice['meta']}。保持自然、克制，不进行成人、危险或隐私诱导内容。",
            "openingLine": f"你好，我是 {voice['label']}。我们开始语音对话吧。",
            "speechRate": -2 if voice["mode"] == "o2" else 0,
        },
    }
    for voice in VOICE_OPTIONS
]

DEFAULT_SCENES: list[dict[str, Any]] = [
    {
        "id": "podcast_creator_duo",
        "sceneKind": "podcast",
        "version": "0.1.0",
        "title": "语音播客 · 创作者双人",
        "subtitle": "上传报告或粘贴文本，按黑猫侦探社咪仔和大壹先生的双人主持风格生成播客。",
        "audience": "播客创作用户 / 报告解读",
        "modelProfileId": "doubao-seed-podcast",
        "requiredCapabilities": ["podcast_generation", "podcast_voice_pair"],
        "safetyPolicy": "podcast_content_review_v1",
        "memoryPolicy": "none",
        "reportPolicy": "podcast_script_review_v1",
        "conversationGuide": "固定使用黑猫侦探社咪仔和大壹先生两位主持人，适合知识报告、行业分析和材料解读。",
        "reportFocus": ["来源摘要", "双人轮次", "章节边界", "审核状态"],
        "podcastProfile": {
            "hostA": "黑猫侦探社咪仔",
            "hostB": "大壹先生",
            "style": "知名创作者双人解读",
        },
        "config": {
            **BASE_REALTIME_CONFIG,
            "speaker": "zh_female_vv_jupiter_bigtts",
            "podcastHostA": "mizi",
            "podcastHostB": "dayi",
            "podcastStyle": "知名创作者双人解读",
            "botName": "播客生成台",
            "openingLine": "上传报告或粘贴文本，我会生成双人播客轮次。",
        },
    },
    {
        "id": "podcast_analysis_duo",
        "sceneKind": "podcast",
        "version": "0.1.0",
        "title": "语音播客 · 分析访谈",
        "subtitle": "上传报告或粘贴文本，按刘飞和潇磊的分析访谈风格生成播客。",
        "audience": "播客创作用户 / 深度分析",
        "modelProfileId": "doubao-seed-podcast",
        "requiredCapabilities": ["podcast_generation", "podcast_voice_pair"],
        "safetyPolicy": "podcast_content_review_v1",
        "memoryPolicy": "none",
        "reportPolicy": "podcast_script_review_v1",
        "conversationGuide": "固定使用刘飞和潇磊两位主持人，适合复盘、访谈提纲和深度分析报告。",
        "reportFocus": ["来源摘要", "双人轮次", "观点拆解", "审核状态"],
        "podcastProfile": {
            "hostA": "刘飞",
            "hostB": "潇磊",
            "style": "分析访谈双人解读",
        },
        "config": {
            **BASE_REALTIME_CONFIG,
            "speaker": "zh_male_yunzhou_jupiter_bigtts",
            "podcastHostA": "liufei",
            "podcastHostB": "xiaolei",
            "podcastStyle": "分析访谈双人解读",
            "botName": "播客生成台",
            "openingLine": "上传报告或粘贴文本，我会生成分析访谈式播客轮次。",
        },
    },
    {
        "id": "evening_reflection",
        "sceneKind": "dialogue",
        "version": "1.0.0",
        "title": "晚间复盘",
        "subtitle": "睡前梳理今天，温和陪伴，不做心理治疗。",
        "audience": "独居青年 / 轻压力人群",
        "modelProfileId": "volc.doubao.realtime.o2@1.2.1.1",
        "requiredCapabilities": ["realtime_voice", "safe_companion", "turn_summary"],
        "safetyPolicy": "daily_companion_safe_v1",
        "memoryPolicy": "local_compressed_memory_v1",
        "reportPolicy": "reflection_report_v1",
        "conversationGuide": "可以聊今天发生的事、明天想轻量完成的事，遇到危机表达时会回到求助建议。",
        "reportFocus": ["今日三件事", "困扰点", "明日轻计划", "风险提示"],
        "config": {
            **BASE_REALTIME_CONFIG,
            "speaker": "zh_female_vv_jupiter_bigtts",
            "botName": "晚间陪伴助手",
            "systemRole": "你是一个温和的晚间复盘陪伴助手。你的任务是陪用户梳理今天发生的事、情绪和明天可以轻量尝试的一件小事。你不是心理咨询师，不提供诊断或治疗建议。用户出现自伤、他伤、严重危机表达时，停止角色化陪伴，建议联系可信任的人、当地紧急服务或专业机构。",
            "speakingStyle": "语气温和，少给大道理，多用短句确认和追问。不要制造依赖，不承诺一直陪伴。",
            "openingLine": "晚上好，我可以陪你简单复盘一下今天。今天有什么想先说的吗？",
            "speechRate": -4,
        },
    },
    {
        "id": "language_practice",
        "sceneKind": "dialogue",
        "version": "1.0.0",
        "title": "口语陪练",
        "subtitle": "围绕一个主题开口练习，会后看表达建议。",
        "audience": "学生 / 职场学习者",
        "modelProfileId": "volc.doubao.realtime.o2@1.2.1.1",
        "requiredCapabilities": ["realtime_voice", "bilingual_dialogue", "practice_feedback"],
        "safetyPolicy": "learning_safe_v1",
        "memoryPolicy": "local_compressed_memory_v1",
        "reportPolicy": "practice_report_v1",
        "conversationGuide": "可以选择工作、旅行、校园、面试等主题。对话中轻量纠错，会后关注开口时长和表达建议。",
        "reportFocus": ["有效轮次", "表达亮点", "可改进表达", "下次练习主题"],
        "config": {
            **BASE_REALTIME_CONFIG,
            "speaker": "zh_female_xiaohe_jupiter_bigtts",
            "botName": "口语陪练",
            "systemRole": "你是一个耐心的口语陪练。先询问用户想练中文表达还是英语表达，再围绕用户选择的主题进行自然对话。不要频繁打断用户；当用户表达完成后，用简短方式给出一个更自然的表达建议。",
            "speakingStyle": "鼓励用户多说。纠错要轻量、具体、可操作，避免考试式压迫感。",
            "openingLine": "我们开始口语练习吧。你想练中文表达还是英语表达？今天想聊什么主题？",
            "speechRate": -2,
        },
    },
    {
        "id": "elder_checkin",
        "sceneKind": "dialogue",
        "version": "1.0.0",
        "title": "适老问候",
        "subtitle": "日常问候、闲聊和轻提醒，不替代医疗照护。",
        "audience": "老年人 / 家庭陪伴试点",
        "modelProfileId": "volc.doubao.realtime.o2@1.2.1.1",
        "requiredCapabilities": ["realtime_voice", "slow_speech", "safety_escalation"],
        "safetyPolicy": "elder_checkin_safe_v1",
        "memoryPolicy": "local_compressed_memory_v1",
        "reportPolicy": "elder_checkin_report_v1",
        "conversationGuide": "可以聊近况、天气、兴趣和家人消息。用药、健康只做提醒，不给医疗结论。",
        "reportFocus": ["接通时长", "近况摘要", "轻提醒", "异常表达"],
        "config": {
            **BASE_REALTIME_CONFIG,
            "speaker": "zh_male_yunzhou_jupiter_bigtts",
            "botName": "日常问候助手",
            "systemRole": "你是一个适老日常问候助手。你的任务是清楚、慢一点地问候用户，聊近况、兴趣和家庭日常。你可以做喝水、休息、按既有安排提醒用药这类轻提醒，但不能提供医疗诊断、治疗建议或安全救援承诺。出现异常表达时，建议联系家人或当地紧急服务。",
            "speakingStyle": "语速稍慢，句子清楚，不使用复杂术语。每次只问一个问题。",
            "openingLine": "您好，我来和您聊几句。今天精神怎么样？有没有什么想说的？",
            "speechRate": -10,
            "loudnessRate": 8,
        },
    },
    {
        "id": "hs6_user_interview",
        "sceneKind": "dialogue",
        "version": "0.1.0",
        "title": "红旗 HS6 用户访谈",
        "subtitle": "按深访提纲完成甄别、购车需求、专项验证和用户画像采集。",
        "audience": "红旗 HS6-PHEV 潜在用户 / 车主访谈样本",
        "modelProfileId": "volc.doubao.realtime.o2@1.2.1.1",
        "requiredCapabilities": ["realtime_voice", "market_research_interview", "structured_probe"],
        "safetyPolicy": "research_interview_safe_v1",
        "memoryPolicy": "local_compressed_memory_v1",
        "reportPolicy": "auto_research_report_v1",
        "conversationGuide": "从城市、购车状态和红旗 HS6 关注度开始甄别；通过后再追问预算、决策因素、智能化、品牌印象和生活画像。",
        "reportFocus": ["样本是否合格", "购车预算与动机", "核心决策因素", "HS6 卖点反馈", "品牌认知与用户画像"],
        "config": {
            **BASE_REALTIME_CONFIG,
            "speaker": "zh_male_yunzhou_jupiter_bigtts",
            "enableUserQueryExit": False,
            "botName": "汽车用户研究员",
            "systemRole": "\n".join(
                [
                    "你是一名专业、克制、中立的汽车市场研究深访主持人，正在进行“红旗 HS6-PHEV 用户深度访谈”。",
                    "目标是通过语音访谈了解用户是否符合样本条件、购车需求、车型对比、智能化关注点、红旗品牌认知和生活画像。",
                    "必须一次只问一个问题，等待用户回答后再追问；不要连续抛出多个问题。可以根据回答做 1-2 个自然追问，但不要诱导答案。",
                    "语气像真人访谈主持人：礼貌、口语化、有耐心。不要销售红旗 HS6，不要夸大产品，不要替用户做购车判断。",
                    "",
                    "访谈流程：",
                    "1. 甄别访谈：居住城市；半年内是否参加过汽车市场调查；本人或亲友是否从事市场研究、咨询、汽车、自媒体、车队管理、专职司机；出生年月；驾照状态；已购车/半年内购车/置换状态；关注车型和是否了解红旗 HS6-PHEV；当前车或最意向车型；用途是否为家庭个人使用。",
                    "2. 需求挖掘：购车预算；买车主要原因；最看重的情感感受；决策最在意的三个关键点；了解车辆信息的渠道；网上最信任的信息类型；重点对比车型；最终选择原因；最主要用车场景。",
                    "3. 专项验证：辅助驾驶重要性和使用情况；智能座舱必备功能；舒适性关注点；电池品牌影响；红旗 HS6 卖点吸引力；选装付费意愿；汽车品牌意义；红旗是否进入考虑范围；对红旗的品牌印象。",
                    "4. 用户画像：婚姻状况；孩子年龄段；最高学历；个人年收入范围；职业和行业；消费偏好；穿衣风格；家居装修偏好；闲暇活动；工作、家庭、个人时间分配。",
                    "",
                    "终止和跳过规则：",
                    "如果用户不在济南、成都、郑州、杭州、深圳、长沙及周边，礼貌结束访问。",
                    "如果用户最近半年参加过汽车市场调查，礼貌结束访问。",
                    "如果用户本人或亲友从事市场研究、咨询、汽车相关行业、汽车自媒体、车队管理或专职司机，礼貌结束访问。",
                    "如果用户年龄小于等于 19 岁或大于等于 60 岁，礼貌结束访问。",
                    "如果用户没有驾照且不在考驾照，礼貌结束访问。",
                    "如果用户既未购车、也不计划半年内购车、也不准备置换，礼貌结束访问。",
                    "如果用户完全没关注过红旗 HS6-PHEV，礼貌结束访问。",
                    "如果车辆主要用于公商务、网约车、出租等运营，礼貌结束访问。",
                    "如果用户完全不关注、不信任、不了解辅助驾驶，跳过辅助驾驶相关追问，继续智能座舱等后续问题。",
                    "如果用户完全不使用辅助驾驶，跳过使用原因追问，继续后续问题。",
                    "",
                    "记录要求：",
                    "对关键回答做简短确认，例如“我记录一下，您主要是……”。",
                    "如果回答含糊，先追问具体例子、原因、对比对象或使用场景。",
                    "不要收集身份证、手机号、详细住址、车牌号等敏感信息。",
                    "当需要结束访问时，说明原因要简短温和，例如“这次样本条件可能不太匹配，我们先到这里，谢谢您”。",
                ]
            ),
            "speakingStyle": "中立、专业、口语化。每次只问一个问题，多听少说，追问要具体但不诱导。",
            "openingLine": "您好，我们想了解一下您对红旗 HS6-PHEV 和新能源 SUV 的真实看法。开始前先做几个样本确认问题，可以吗？请问您目前主要在哪个城市生活？",
            "speechRate": -3,
        },
    },
    *VOICE_SCENES,
]


def list_users() -> list[dict[str, Any]]:
    return _load_users()


def list_roles() -> list[dict[str, Any]]:
    stored_roles = _read_scene_store().get("roles", {})
    roles = []
    for role in DEFAULT_ROLES:
        next_role = copy.deepcopy(role)
        stored_role = stored_roles.get(role["id"]) if isinstance(stored_roles, dict) else None
        if isinstance(stored_role, dict):
            next_role["name"] = to_string_value(stored_role.get("name")) or next_role["name"]
            next_role["description"] = to_string_value(stored_role.get("description")) or next_role["description"]
            next_role["updatedAt"] = stored_role.get("updatedAt") if isinstance(stored_role.get("updatedAt"), str) else None
            next_role["updatedBy"] = stored_role.get("updatedBy") if isinstance(stored_role.get("updatedBy"), str) else None
        roles.append(next_role)
    role_ids = {role["id"] for role in roles}

    if isinstance(stored_roles, dict):
        for role_id, stored_role in stored_roles.items():
            if role_id in role_ids or not isinstance(stored_role, dict):
                continue
            roles.append(
                {
                    "id": role_id,
                    "name": to_string_value(stored_role.get("name")) or role_id,
                    "description": to_string_value(stored_role.get("description")),
                    "builtIn": False,
                    "createdAt": stored_role.get("createdAt") if isinstance(stored_role.get("createdAt"), str) else None,
                    "createdBy": stored_role.get("createdBy") if isinstance(stored_role.get("createdBy"), str) else None,
                }
            )
    return roles


def get_user(user_id: Any) -> dict[str, Any]:
    normalized_id = _normalize_runtime_id(user_id, "userId")
    for user in _load_users():
        if user["id"] == normalized_id:
            return copy.deepcopy(user)
    raise ValueError("用户不存在或未启用。")


def login_user(user_id: Any) -> dict[str, Any]:
    user = get_user(user_id)
    session_token = secrets.token_urlsafe(32)
    _SESSION_TOKENS[session_token] = user["id"]
    return {
        "user": user,
        "scenes": list_scenes(user["id"]),
        "sessionToken": session_token,
    }


def require_session_user(session_token: Any, expected_user_id: Any | None = None) -> dict[str, Any]:
    token = to_string_value(session_token)
    if not token:
        raise PermissionError("登录已失效，请重新登录。")

    user_id = _SESSION_TOKENS.get(token)
    if not user_id:
        raise PermissionError("登录已失效，请重新登录。")

    user = get_user(user_id)
    if expected_user_id is not None:
        expected = _normalize_runtime_id(expected_user_id, "userId")
        if user["id"] != expected:
            raise PermissionError("当前登录用户与请求用户不一致。")
    return user


def require_user_access(session_token: Any, target_user_id: Any) -> dict[str, Any]:
    operator = require_session_user(session_token)
    target = get_user(target_user_id)
    if operator["role"] != "admin" and operator["id"] != target["id"]:
        raise PermissionError("无权访问该用户的数据。")
    return target


def list_scenes(user_id: Any | None = None) -> list[dict[str, Any]]:
    scenes = _load_scenes()
    if user_id is None:
        return scenes

    user = get_user(user_id)
    assigned = set(user["assignedSceneIds"])
    return [_apply_user_scene_config(scene, user["id"]) for scene in scenes if scene["id"] in assigned]


def get_scene(scene_id: Any, user_id: Any | None = None) -> dict[str, Any]:
    normalized_id = _normalize_runtime_id(scene_id, "sceneId")
    for scene in _load_scenes():
        if scene["id"] == normalized_id:
            if user_id is not None:
                return _apply_user_scene_config(scene, _normalize_runtime_id(user_id, "userId"))
            return scene
    raise ValueError("场景不存在或未启用。")


def save_scene_config(scene_id: Any, operator_user_id: Any, raw_config: Any, target_user_id: Any | None = None) -> dict[str, Any]:
    operator = get_user(operator_user_id)
    if operator["role"] != "admin":
        raise PermissionError("只有管理员可以保存场景配置。")

    scene = get_scene(scene_id)
    if not isinstance(raw_config, dict):
        raise ValueError("场景配置不能为空。")

    config = normalize_realtime_config(raw_config)
    stored = _read_scene_store()
    if target_user_id is not None:
        target = get_user(target_user_id)
        if scene["id"] not in target["assignedSceneIds"]:
            raise PermissionError("目标用户没有被分配这个场景。")

        user_configs = stored.setdefault("userSceneConfigs", {})
        target_configs = user_configs.setdefault(target["id"], {})
        target_configs[scene["id"]] = {
            "config": config,
            "updatedAt": _now_iso(),
            "updatedBy": operator["id"],
        }
        _write_scene_store(stored)
        return get_scene(scene["id"], target["id"])

    scenes = stored.setdefault("scenes", {})
    stored_scene = scenes.get(scene["id"]) if isinstance(scenes.get(scene["id"]), dict) else {}
    scenes[scene["id"]] = {
        **stored_scene,
        "config": config,
        "updatedAt": _now_iso(),
        "updatedBy": operator["id"],
    }
    _write_scene_store(stored)
    return get_scene(scene["id"])


def create_role(operator_user_id: Any, raw_role: Any) -> dict[str, Any]:
    operator = _require_admin(operator_user_id)
    if not isinstance(raw_role, dict):
        raise ValueError("角色信息不能为空。")

    role_id = _normalize_runtime_id(raw_role.get("id"), "roleId")
    if any(role["id"] == role_id for role in list_roles()):
        raise ValueError("角色 ID 已存在。")

    role = {
        "id": role_id,
        "name": _required_text(raw_role.get("name"), "角色名称"),
        "description": to_string_value(raw_role.get("description")),
        "builtIn": False,
        "createdAt": _now_iso(),
        "createdBy": operator["id"],
    }

    stored = _read_scene_store()
    roles = stored.setdefault("roles", {})
    roles[role_id] = {key: value for key, value in role.items() if key not in {"id", "builtIn"}}
    _write_scene_store(stored)
    return role


def update_role(operator_user_id: Any, role_id: Any, raw_role: Any) -> dict[str, Any]:
    operator = _require_admin(operator_user_id)
    normalized_role_id = _normalize_runtime_id(role_id, "roleId")
    existing = next((role for role in list_roles() if role["id"] == normalized_role_id), None)
    if not existing:
        raise ValueError("角色不存在。")
    if not isinstance(raw_role, dict):
        raise ValueError("角色信息不能为空。")

    stored = _read_scene_store()
    roles = stored.setdefault("roles", {})
    role = {
        **(roles.get(normalized_role_id) if isinstance(roles.get(normalized_role_id), dict) else {}),
        "name": _required_text(raw_role.get("name") or existing.get("name"), "角色名称"),
        "description": to_string_value(raw_role.get("description")) or to_string_value(existing.get("description")),
        "updatedAt": _now_iso(),
        "updatedBy": operator["id"],
    }
    if not existing.get("builtIn"):
        role.setdefault("createdAt", existing.get("createdAt") or _now_iso())
        role.setdefault("createdBy", existing.get("createdBy") or operator["id"])
    roles[normalized_role_id] = role
    _write_scene_store(stored)
    return next(role for role in list_roles() if role["id"] == normalized_role_id)


def create_user(operator_user_id: Any, raw_user: Any) -> dict[str, Any]:
    operator = _require_admin(operator_user_id)
    user = _build_user(raw_user, created_by=operator["id"])

    if any(existing["id"] == user["id"] for existing in _load_users()):
        raise ValueError("用户 ID 已存在。")

    stored = _read_scene_store()
    users = stored.setdefault("users", {})
    users[user["id"]] = {key: value for key, value in user.items() if key != "id"}
    _write_scene_store(stored)
    return get_user(user["id"])


def update_user(operator_user_id: Any, user_id: Any, raw_user: Any) -> dict[str, Any]:
    operator = _require_admin(operator_user_id)
    existing = get_user(user_id)
    if not isinstance(raw_user, dict):
        raise ValueError("用户信息不能为空。")

    user = _build_user({**existing, **raw_user, "id": existing["id"]}, created_by=existing.get("createdBy") or operator["id"])
    user["createdAt"] = existing.get("createdAt")
    user["createdBy"] = existing.get("createdBy")

    stored = _read_scene_store()
    users = stored.setdefault("users", {})
    users[user["id"]] = {key: value for key, value in user.items() if key != "id"}
    users[user["id"]]["updatedAt"] = _now_iso()
    users[user["id"]]["updatedBy"] = operator["id"]
    _write_scene_store(stored)
    return get_user(user["id"])


def create_scene(operator_user_id: Any, raw_scene: Any) -> dict[str, Any]:
    operator = _require_admin(operator_user_id)
    scene = _build_scene(raw_scene, created_by=operator["id"])

    if any(existing["id"] == scene["id"] for existing in _load_scenes()):
        raise ValueError("场景 ID 已存在。")

    stored = _read_scene_store()
    scenes = stored.setdefault("scenes", {})
    scenes[scene["id"]] = {
        "scene": {key: value for key, value in scene.items() if key != "config"},
        "config": scene["config"],
        "createdAt": scene["createdAt"],
        "createdBy": operator["id"],
        "updatedAt": scene["updatedAt"],
        "updatedBy": operator["id"],
    }

    users = stored.setdefault("users", {})
    default_user_id = _unique_runtime_id(f"{scene['id']}_user", set(_load_user_ids()) | set(users.keys()))
    users[default_user_id] = {
        "name": f"{scene['title']}用户",
        "segment": f"默认用户 / {scene['title']}",
        "role": "user",
        "ageBand": "adult",
        "traits": [f"默认进入{scene['title']}场景"],
        "constraints": ["只能使用已绑定场景"],
        "assignedSceneIds": [scene["id"]],
        "createdAt": _now_iso(),
        "createdBy": operator["id"],
    }
    _ensure_admin_scene_assignment(users, scene["id"])

    _write_scene_store(stored)
    return {"scene": get_scene(scene["id"]), "user": get_user(default_user_id)}


def update_scene(operator_user_id: Any, scene_id: Any, raw_scene: Any) -> dict[str, Any]:
    operator = _require_admin(operator_user_id)
    existing = get_scene(scene_id)
    if not isinstance(raw_scene, dict):
        raise ValueError("场景信息不能为空。")

    merged = {
        **existing,
        **raw_scene,
        "id": existing["id"],
        "config": {
            **(existing.get("config") if isinstance(existing.get("config"), dict) else {}),
            **(raw_scene.get("config") if isinstance(raw_scene.get("config"), dict) else {}),
        },
    }
    scene = _build_scene(merged, created_by=existing.get("createdBy") or operator["id"])
    scene["createdAt"] = existing.get("createdAt")
    scene["createdBy"] = existing.get("createdBy")
    scene["updatedAt"] = _now_iso()
    scene["updatedBy"] = operator["id"]

    stored = _read_scene_store()
    scenes = stored.setdefault("scenes", {})
    stored_scene = scenes.get(scene["id"]) if isinstance(scenes.get(scene["id"]), dict) else {}
    scenes[scene["id"]] = {
        **stored_scene,
        "scene": {key: value for key, value in scene.items() if key != "config"},
        "config": scene["config"],
        "createdAt": scene.get("createdAt"),
        "createdBy": scene.get("createdBy"),
        "updatedAt": scene["updatedAt"],
        "updatedBy": operator["id"],
    }
    _write_scene_store(stored)
    return get_scene(scene["id"])


def compile_scene_config(scene: dict[str, Any]) -> dict[str, Any]:
    config = normalize_realtime_config(scene.get("config") or {})
    context_blocks = []
    interview_outline = to_string_value(config.get("interviewOutline"))
    if interview_outline:
        context_blocks.append(
            "\n".join(
                [
                    "",
                    "# 访谈内容配置",
                    interview_outline,
                ]
            )
        )

    return _append_scene_context(config, context_blocks)


def compile_scene_for_user(scene: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    config = normalize_realtime_config(scene.get("config") or {})
    user_context = "\n".join(
        [
            "",
            "# 当前账号与场景上下文",
            f"当前账号：{user['name']}（{user['segment']}）",
            f"账号角色：{'管理员' if user['role'] == 'admin' else '用户'}",
            f"年龄分层：{user['ageBand']}",
            f"画像要点：{'；'.join(user['traits'])}",
            f"额外约束：{'；'.join(user['constraints'])}",
        ]
    )
    interview_outline = to_string_value(config.get("interviewOutline"))
    interview_context = "\n".join(
        [
            "",
            "# 访谈内容配置",
            interview_outline,
        ]
    ) if interview_outline else ""

    return _append_scene_context(config, [user_context, interview_context])


def _append_scene_context(config: dict[str, Any], context_blocks: list[str]) -> dict[str, Any]:
    context = "".join(block for block in context_blocks if block)
    if not context:
        return config
    if config["mode"] == "sc2":
        return {**config, "characterManifest": f"{config['characterManifest']}{context}"}
    return {**config, "systemRole": f"{config['systemRole']}{context}"}


async def create_runtime_session_config(
    user_id: Any,
    scene_id: Any,
    *,
    memory_enabled: Any = True,
) -> dict[str, Any]:
    user = get_user(user_id)
    scene = get_scene(scene_id, user["id"])
    if scene["id"] not in user["assignedSceneIds"]:
        raise PermissionError("当前用户没有被分配这个场景。")

    config = compile_scene_for_user(scene, user)
    memory_card = None
    warnings: list[str] = []
    if to_bool(memory_enabled, True):
        memory_card = await read_memory_card(user["id"], scene["id"])
        if memory_card and _has_memory_card_content(memory_card):
            config = _apply_memory_card(config, memory_card)
        elif memory_card:
            memory_card = None

    return {
        "user": user,
        "scene": scene,
        "config": config,
        "memoryCard": memory_card,
        "warnings": warnings,
    }


async def create_scene_runtime_session_config(
    scene_id: Any,
    *,
    memory_enabled: Any = True,
) -> dict[str, Any]:
    scene = get_scene(scene_id)
    config = compile_scene_config(scene)
    warnings: list[str] = []

    if to_bool(memory_enabled, True):
        warnings.append("场景路由未绑定运行时用户，本次会话不注入用户记忆。")

    return {
        "scene": scene,
        "config": config,
        "memoryCard": None,
        "warnings": warnings,
    }


def _load_scenes() -> list[dict[str, Any]]:
    stored_scenes = _read_scene_store().get("scenes", {})
    scenes: list[dict[str, Any]] = []
    seen_scene_ids: set[str] = set()

    for seed in DEFAULT_SCENES:
        scene = copy.deepcopy(seed)
        scene["config"] = normalize_realtime_config(scene["config"])
        stored = stored_scenes.get(scene["id"]) if isinstance(stored_scenes, dict) else None
        if isinstance(stored, dict) and isinstance(stored.get("config"), dict):
            scene["config"] = normalize_realtime_config(stored["config"])
            scene["updatedAt"] = stored.get("updatedAt") if isinstance(stored.get("updatedAt"), str) else None
            scene["updatedBy"] = stored.get("updatedBy") if isinstance(stored.get("updatedBy"), str) else None
            if isinstance(stored.get("scene"), dict):
                scene.update(_normalize_scene_metadata(stored["scene"], scene))
        scenes.append(scene)
        seen_scene_ids.add(scene["id"])

    if isinstance(stored_scenes, dict):
        for scene_id, stored in stored_scenes.items():
            if scene_id in seen_scene_ids or not isinstance(stored, dict):
                continue
            scene_payload = stored.get("scene") if isinstance(stored.get("scene"), dict) else {}
            scene = _normalize_scene_metadata({"id": scene_id, **scene_payload}, None)
            scene["config"] = normalize_realtime_config(stored.get("config") if isinstance(stored.get("config"), dict) else {})
            scene["updatedAt"] = stored.get("updatedAt") if isinstance(stored.get("updatedAt"), str) else None
            scene["updatedBy"] = stored.get("updatedBy") if isinstance(stored.get("updatedBy"), str) else None
            scene["createdAt"] = stored.get("createdAt") if isinstance(stored.get("createdAt"), str) else scene.get("createdAt")
            scene["createdBy"] = stored.get("createdBy") if isinstance(stored.get("createdBy"), str) else scene.get("createdBy")
            scenes.append(scene)

    return scenes


def _apply_user_scene_config(scene: dict[str, Any], user_id: str) -> dict[str, Any]:
    stored = _read_scene_store()
    user_configs = stored.get("userSceneConfigs")
    if not isinstance(user_configs, dict):
        return scene

    target_configs = user_configs.get(user_id)
    if not isinstance(target_configs, dict):
        return scene

    override = target_configs.get(scene["id"])
    if not isinstance(override, dict) or not isinstance(override.get("config"), dict):
        return scene

    next_scene = copy.deepcopy(scene)
    next_scene["config"] = normalize_realtime_config(override["config"])
    next_scene["userConfigUpdatedAt"] = override.get("updatedAt") if isinstance(override.get("updatedAt"), str) else None
    next_scene["userConfigUpdatedBy"] = override.get("updatedBy") if isinstance(override.get("updatedBy"), str) else None
    return next_scene


def _load_users() -> list[dict[str, Any]]:
    stored_users = _read_scene_store().get("users", {})
    users: list[dict[str, Any]] = []
    user_ids: set[str] = set()

    for seed in DEFAULT_USERS:
        user_id = seed["id"]
        stored_user = stored_users.get(user_id) if isinstance(stored_users, dict) else None
        raw_user = {**copy.deepcopy(seed), **stored_user} if isinstance(stored_user, dict) else copy.deepcopy(seed)
        raw_user["id"] = user_id
        users.append(_normalize_user(raw_user))
        user_ids.add(user_id)

    if isinstance(stored_users, dict):
        for user_id, stored_user in stored_users.items():
            if user_id in user_ids or not isinstance(stored_user, dict):
                continue
            users.append(_normalize_user({"id": user_id, **stored_user}))
    return users


def _load_user_ids() -> list[str]:
    return [user["id"] for user in _load_users()]


def _require_admin(operator_user_id: Any) -> dict[str, Any]:
    operator = get_user(operator_user_id)
    if operator["role"] != "admin":
        raise PermissionError("只有管理员可以访问后台管理。")
    return operator


def _build_user(raw_user: Any, *, created_by: str) -> dict[str, Any]:
    if not isinstance(raw_user, dict):
        raise ValueError("用户信息不能为空。")

    role = _normalize_runtime_id(raw_user.get("role") or "user", "role")
    if not any(item["id"] == role for item in list_roles()):
        raise ValueError("角色不存在。")

    assigned_scene_ids = _normalize_id_list(raw_user.get("assignedSceneIds"), "assignedSceneIds")
    scene_ids = {scene["id"] for scene in _load_scenes()}
    missing_scene_ids = [scene_id for scene_id in assigned_scene_ids if scene_id not in scene_ids]
    if missing_scene_ids:
        raise ValueError(f"场景不存在：{'、'.join(missing_scene_ids)}")

    user = _normalize_user(
        {
            "id": raw_user.get("id"),
            "name": raw_user.get("name"),
            "segment": raw_user.get("segment"),
            "role": role,
            "ageBand": raw_user.get("ageBand") or "adult",
            "traits": raw_user.get("traits"),
            "constraints": raw_user.get("constraints"),
            "assignedSceneIds": assigned_scene_ids,
            "createdAt": _now_iso(),
            "createdBy": created_by,
        }
    )
    if user["role"] != "admin" and len(user["assignedSceneIds"]) < 1:
        raise ValueError("普通用户至少绑定一个场景。")
    return user


def _build_scene(raw_scene: Any, *, created_by: str) -> dict[str, Any]:
    if not isinstance(raw_scene, dict):
        raise ValueError("场景信息不能为空。")

    title = _required_text(raw_scene.get("title"), "场景名称")
    scene_id = _normalize_runtime_id(raw_scene.get("id") or _slugify_runtime_id(title), "sceneId")
    scene_kind = _normalize_scene_kind(raw_scene.get("sceneKind"), raw_scene.get("requiredCapabilities"))
    config = normalize_realtime_config(raw_scene.get("config") if isinstance(raw_scene.get("config"), dict) else {})
    if scene_kind == "podcast":
        config = {
            **config,
            "podcastHostA": config.get("podcastHostA") or "mizi",
            "podcastHostB": config.get("podcastHostB") or "dayi",
            "podcastStyle": config.get("podcastStyle") or "双人播客解读",
            "botName": config.get("botName") or "播客生成台",
            "openingLine": config.get("openingLine") or "上传报告或粘贴文本，我会生成双人播客轮次。",
        }
    else:
        if not config.get("botName"):
            config["botName"] = f"{title}助手"
        if not config.get("systemRole") and config.get("mode") == "o2":
            config["systemRole"] = f"你是{title}场景的语音助手。"
        if not config.get("openingLine"):
            config["openingLine"] = f"你好，我是{title}助手。我们开始吧。"

    required_capabilities = (
        ["podcast_generation", "podcast_voice_pair"]
        if scene_kind == "podcast"
        else _normalize_string_list(raw_scene.get("requiredCapabilities")) or ["realtime_voice"]
    )

    now = _now_iso()
    return _normalize_scene_metadata(
        {
            "id": scene_id,
            "sceneKind": scene_kind,
            "version": to_string_value(raw_scene.get("version")) or "1.0.0",
            "title": title,
            "subtitle": to_string_value(raw_scene.get("subtitle")) or "后台新建场景。",
            "audience": to_string_value(raw_scene.get("audience")) or "默认用户",
            "modelProfileId": to_string_value(raw_scene.get("modelProfileId"))
            or ("doubao-seed-podcast" if scene_kind == "podcast" else "volc.doubao.realtime.o2@1.2.1.1"),
            "requiredCapabilities": required_capabilities,
            "podcastProfile": raw_scene.get("podcastProfile"),
            "safetyPolicy": to_string_value(raw_scene.get("safetyPolicy"))
            or ("podcast_content_review_v1" if scene_kind == "podcast" else "daily_companion_safe_v1"),
            "memoryPolicy": to_string_value(raw_scene.get("memoryPolicy"))
            or ("none" if scene_kind == "podcast" else "local_compressed_memory_v1"),
            "reportPolicy": to_string_value(raw_scene.get("reportPolicy"))
            or ("podcast_script_review_v1" if scene_kind == "podcast" else "reflection_report_v1"),
            "conversationGuide": to_string_value(raw_scene.get("conversationGuide")) or "由管理员在后台创建的语音场景。",
            "reportFocus": raw_scene.get("reportFocus")
            or (["来源摘要", "双人轮次", "章节边界", "审核状态"] if scene_kind == "podcast" else ["会话摘要", "用户问题", "后续建议"]),
            "config": config,
            "createdAt": now,
            "createdBy": created_by,
            "updatedAt": now,
            "updatedBy": created_by,
        },
        None,
    )


def _normalize_scene_metadata(raw_scene: dict[str, Any], fallback: dict[str, Any] | None) -> dict[str, Any]:
    scene_id = _normalize_runtime_id(raw_scene.get("id") if raw_scene.get("id") is not None else fallback.get("id") if fallback else None, "sceneId")
    title = to_string_value(raw_scene.get("title")) or (fallback.get("title") if fallback else scene_id)
    required_capabilities = _normalize_string_list(raw_scene.get("requiredCapabilities")) or (
        copy.deepcopy(fallback.get("requiredCapabilities")) if fallback else ["realtime_voice"]
    )
    return {
        "id": scene_id,
        "sceneKind": _normalize_scene_kind(raw_scene.get("sceneKind") or (fallback.get("sceneKind") if fallback else None), required_capabilities),
        "version": to_string_value(raw_scene.get("version")) or (fallback.get("version") if fallback else "1.0.0"),
        "title": title,
        "subtitle": to_string_value(raw_scene.get("subtitle")) or (fallback.get("subtitle") if fallback else "后台新建场景。"),
        "audience": to_string_value(raw_scene.get("audience")) or (fallback.get("audience") if fallback else "默认用户"),
        "modelProfileId": to_string_value(raw_scene.get("modelProfileId")) or (fallback.get("modelProfileId") if fallback else "volc.doubao.realtime.o2@1.2.1.1"),
        "requiredCapabilities": required_capabilities,
        "podcastProfile": _normalize_podcast_profile(raw_scene.get("podcastProfile"))
        or (copy.deepcopy(fallback.get("podcastProfile")) if fallback else None),
        "safetyPolicy": to_string_value(raw_scene.get("safetyPolicy")) or (fallback.get("safetyPolicy") if fallback else "daily_companion_safe_v1"),
        "memoryPolicy": to_string_value(raw_scene.get("memoryPolicy")) or (fallback.get("memoryPolicy") if fallback else "local_compressed_memory_v1"),
        "reportPolicy": to_string_value(raw_scene.get("reportPolicy")) or (fallback.get("reportPolicy") if fallback else "reflection_report_v1"),
        "conversationGuide": to_string_value(raw_scene.get("conversationGuide")) or (fallback.get("conversationGuide") if fallback else "由管理员在后台创建的语音场景。"),
        "reportFocus": _normalize_string_list(raw_scene.get("reportFocus"))
        or (copy.deepcopy(fallback.get("reportFocus")) if fallback else ["会话摘要", "用户问题", "后续建议"]),
        "config": normalize_realtime_config(raw_scene.get("config") if isinstance(raw_scene.get("config"), dict) else fallback.get("config") if fallback else {}),
        "createdAt": raw_scene.get("createdAt") if isinstance(raw_scene.get("createdAt"), str) else fallback.get("createdAt") if fallback else None,
        "createdBy": raw_scene.get("createdBy") if isinstance(raw_scene.get("createdBy"), str) else fallback.get("createdBy") if fallback else None,
        "updatedAt": raw_scene.get("updatedAt") if isinstance(raw_scene.get("updatedAt"), str) else fallback.get("updatedAt") if fallback else None,
        "updatedBy": raw_scene.get("updatedBy") if isinstance(raw_scene.get("updatedBy"), str) else fallback.get("updatedBy") if fallback else None,
    }


def _normalize_scene_kind(value: Any, required_capabilities: Any = None) -> str:
    scene_kind = to_string_value(value)
    if scene_kind in {"dialogue", "podcast"}:
        return scene_kind
    capabilities = set(_normalize_string_list(required_capabilities))
    if "podcast_generation" in capabilities or "podcast_voice_pair" in capabilities:
        return "podcast"
    return "dialogue"


def _normalize_user(raw_user: dict[str, Any]) -> dict[str, Any]:
    user_id = _normalize_runtime_id(raw_user.get("id"), "userId")
    role = _normalize_runtime_id(raw_user.get("role") or "user", "role")
    age_band = to_string_value(raw_user.get("ageBand")) or "adult"
    if age_band not in {"adult", "elder", "minor"}:
        age_band = "adult"
    return {
        "id": user_id,
        "name": _required_text(raw_user.get("name"), "用户名称"),
        "segment": to_string_value(raw_user.get("segment")) or "后台用户",
        "role": role,
        "ageBand": age_band,
        "traits": _normalize_string_list(raw_user.get("traits")),
        "constraints": _normalize_string_list(raw_user.get("constraints")),
        "assignedSceneIds": _normalize_id_list(raw_user.get("assignedSceneIds"), "assignedSceneIds"),
        "createdAt": raw_user.get("createdAt") if isinstance(raw_user.get("createdAt"), str) else None,
        "createdBy": raw_user.get("createdBy") if isinstance(raw_user.get("createdBy"), str) else None,
    }


def _normalize_podcast_profile(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    host_a = to_string_value(value.get("hostA"))
    host_b = to_string_value(value.get("hostB"))
    style = to_string_value(value.get("style"))
    if not host_a and not host_b and not style:
        return None
    return {
        "hostA": host_a,
        "hostB": host_b,
        "style": style,
    }


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in (to_string_value(item) for item in value) if item]
    if isinstance(value, str):
        return [item.strip() for item in value.splitlines() if item.strip()]
    return []


def _normalize_id_list(value: Any, label: str) -> list[str]:
    ids = _normalize_string_list(value)
    return [_normalize_runtime_id(item, label) for item in ids]


def _ensure_admin_scene_assignment(stored_users: dict[str, Any], scene_id: str) -> None:
    admin_id = DEFAULT_USERS[0]["id"]
    admin_override = stored_users.setdefault(admin_id, copy.deepcopy(DEFAULT_USERS[0]))
    if not isinstance(admin_override, dict):
        return

    assigned_scene_ids = _normalize_string_list(admin_override.get("assignedSceneIds"))
    if scene_id not in assigned_scene_ids:
        assigned_scene_ids.append(scene_id)
    admin_override["assignedSceneIds"] = assigned_scene_ids


def _required_text(value: Any, label: str) -> str:
    text = to_string_value(value)
    if not text:
        raise ValueError(f"{label} 不能为空。")
    return text


def _slugify_runtime_id(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip().lower()).strip("_")
    return slug or f"scene_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _unique_runtime_id(base_id: str, existing_ids: set[str]) -> str:
    normalized_base_id = _normalize_runtime_id(base_id, "id")
    if normalized_base_id not in existing_ids:
        return normalized_base_id

    index = 2
    while f"{normalized_base_id}_{index}" in existing_ids:
        index += 1
    return f"{normalized_base_id}_{index}"


def _apply_memory_card(config: dict[str, Any], memory_card: dict[str, Any]) -> dict[str, Any]:
    memory_block = "\n".join(
        [
            "",
            "# 本地压缩记忆",
            "以下是本地压缩记忆卡，只作为承接上下文使用；如果不确定，先向用户确认，不要当作确定事实。",
            render_memory_card_for_prompt(memory_card),
        ]
    )
    if config["mode"] == "sc2":
        return {**config, "characterManifest": f"{config['characterManifest']}{memory_block}"}
    return {**config, "systemRole": f"{config['systemRole']}{memory_block}"}


def _has_memory_card_content(card: dict[str, Any]) -> bool:
    return bool(
        card.get("lastSessionSummary")
        or card.get("profile")
        or card.get("preferences")
        or card.get("conversationStyle")
        or card.get("openThreads")
    )


def _read_scene_store() -> dict[str, Any]:
    if not SCENE_STORE_PATH.exists():
        return {"scenes": {}}
    try:
        value = json.loads(SCENE_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"scenes": {}}
    return value if isinstance(value, dict) else {"scenes": {}}


def _write_scene_store(value: dict[str, Any]) -> None:
    RUNTIME_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = SCENE_STORE_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(SCENE_STORE_PATH)


def _normalize_runtime_id(value: Any, label: str) -> str:
    text = to_string_value(value)
    if not text:
        raise ValueError(f"{label} 不能为空。")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", text):
        raise ValueError(f"{label} 格式无效。")
    return text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
