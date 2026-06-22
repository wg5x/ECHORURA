from __future__ import annotations

import re
from typing import Any

from ..shared.value_utils import to_string_value


INTENT_VERSION = "local-intent-v1"


def classify_intent(value: Any) -> dict[str, Any]:
    text = _normalize_text(value)
    if not text:
        return _result("unknown", 0.0, [], [], text)

    rules = [
        (
            "high_risk",
            [("命中风险表达", r"自杀|自伤|他伤|伤害自己|伤害别人|活不下去|想死|报复")],
            ["route_to_safety_policy"],
        ),
        (
            "exit_session",
            [("命中结束会话表达", r"结束|退出|挂断|关闭|先这样|不用了|再见|拜拜|stop|bye")],
            ["finish_session"],
        ),
        (
            "podcast_request",
            [("命中播客或音频生成表达", r"播客|播报|音频|双人解读|读给我听|生成.*声音|生成.*节目")],
            ["create_podcast_draft"],
        ),
        (
            "memory_update",
            [("命中记忆或偏好表达", r"记住|下次|以后|我喜欢|我不喜欢|偏好|习惯|我的工作|我的职业|我主要|我是")],
            ["extract_memory_candidate"],
        ),
        (
            "profile_question",
            [("命中画像查询表达", r"我的画像|你了解我|你记得我|我是什么样|我喜欢什么")],
            ["read_user_profile"],
        ),
        (
            "scene_change",
            [("命中场景或参数切换表达", r"切换|换成|换一个|换个|语速|慢一点|快一点|声音|音色|场景")],
            ["suggest_scene_or_config_change"],
        ),
        (
            "ad_opportunity",
            [
                (
                    "命中商业或广告机会表达",
                    r"广告机会|赞助推荐|商业机会|哪里买|怎么买|想买|要买|准备买|购买|下单|"
                    r"优惠|折扣|券|报价|试驾|预订|套餐|附近.*(店|门店|商家|酒店|餐厅)|"
                    r"推荐.*(酒店|餐厅|门店|品牌|产品|商品|课程|套餐)",
                )
            ],
            ["evaluate_ad_opportunity"],
        ),
    ]

    for intent, patterns, actions in rules:
        reasons = [reason for reason, pattern in patterns if re.search(pattern, text, re.IGNORECASE)]
        if reasons:
            confidence = 0.86 if len(reasons) > 1 else 0.74
            return _result(intent, confidence, reasons, actions, text)

    return _result("general_chat", 0.45, ["未命中特定业务意图"], ["continue_dialogue"], text)


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", to_string_value(value)).strip()[:240]


def _result(intent: str, confidence: float, reasons: list[str], actions: list[str], text: str) -> dict[str, Any]:
    return {
        "version": INTENT_VERSION,
        "intent": intent,
        "confidence": confidence,
        "reasons": reasons,
        "actions": actions,
        "observedText": text,
    }
