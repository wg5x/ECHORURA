from __future__ import annotations

import re

from .models import Capability, RouteDecision, RouteInput


class RuleBasedStrategy:
    def decide(self, route_input: RouteInput, capabilities: list[Capability]) -> RouteDecision:
        text = _normalize_text(route_input.text)
        capability = _match_capability(text, capabilities)
        arguments = dict(capability.arguments)
        arguments.update(_extract_arguments(capability, route_input.text, text))

        decision: RouteDecision = {
            "type": "route_decision",
            "session_id": route_input.session_id,
            "turn_id": route_input.turn_id,
            "agent_profile_id": route_input.agent_profile_id,
            "mode": capability.mode,
            "intent": capability.intent,
            "confidence": capability.confidence,
            "need_clarification": False,
            "requires_confirmation": capability.requires_confirmation,
            "arguments": arguments,
        }

        if capability.mode == "scenario":
            decision["scenario_id"] = capability.scenario_id
            decision["scenario_intent"] = capability.scenario_intent

        return decision


def _match_capability(text: str, capabilities: list[Capability]) -> Capability:
    fallback = capabilities[-1]
    for capability in capabilities:
        if not capability.keywords:
            fallback = capability
            continue
        if capability.id == "native.calendar.create_event":
            if _is_calendar_event_request(text):
                return capability
            continue
        if any(_normalize_text(keyword) in text for keyword in capability.keywords):
            return capability
    return fallback


def _extract_arguments(capability: Capability, raw_text: str, normalized_text: str) -> dict[str, str]:
    if capability.id == "native.calendar.create_event":
        return _extract_calendar_event_arguments(raw_text)
    if capability.id == "native.phone.dial":
        return _extract_phone_dial_arguments(raw_text)
    if capability.id == "native.sms.compose":
        return _extract_sms_compose_arguments(raw_text)
    if capability.id == "native.app.open":
        return _extract_app_open_arguments(raw_text)
    if capability.id == "native.app.search":
        return _extract_app_search_arguments(raw_text)
    if capability.id == "native.app.open_deep_link":
        return _extract_app_deep_link_arguments(raw_text)
    if capability.id == "native.browser.open_url":
        return _extract_browser_open_url_arguments(raw_text)
    if capability.id == "native.gallery.pick_image":
        return {"media_type": "image"}
    if capability.id == "native.media.play_from_search":
        return _extract_media_play_arguments(raw_text, normalized_text)
    if capability.id == "native.settings.open_wifi":
        return {"panel": "wifi"}
    if capability.id == "native.camera.capture_photo":
        return {"media_type": "image"}
    if capability.id == "native.camera.capture_video":
        return {"media_type": "video"}
    if capability.id == "server.memory.preference_update":
        return _extract_memory_update_arguments(raw_text)
    if capability.id == "music_creation.create_song":
        return _extract_create_song_arguments(raw_text, normalized_text)
    if capability.id == "music_creation.revise_song":
        return {"revision_prompt": raw_text.strip()}
    return {}


def _is_calendar_event_request(text: str) -> bool:
    if any(marker in text for marker in ("发短信", "发信息", "发消息", "短信", "发微信", "微信发给", "副歌")):
        return False
    if any(marker in text for marker in ("天气", "气温", "下雨", "温度", "多少度")):
        return False

    action_markers = ("开会", "会议", "日程", "提醒", "记录", "创建", "新增", "添加", "评审", "面试")
    time_markers = ("今天", "明天", "后天", "上午", "中午", "下午", "晚上")
    if _has_clock_time(text) and (
        any(marker in text for marker in action_markers) or any(marker in text for marker in time_markers)
    ):
        return True
    return any(marker in text for marker in action_markers) and any(marker in text for marker in time_markers)


def _has_clock_time(text: str) -> bool:
    return bool(
        re.search(r"(今天|明天|后天)?(上午|中午|下午|晚上)?[一二两三四五六七八九十\d]+点半?", text)
        or re.search(r"(今天|明天|后天)?\d{1,2}:\d{2}", text)
    )


def _extract_calendar_event_arguments(raw_text: str) -> dict[str, str]:
    text = raw_text.strip()
    time_text = _first_match_text(
        text,
        (
            r"(今天|明天|后天)?(上午|中午|下午|晚上)?[一二两三四五六七八九十\d]+点半?",
            r"(今天|明天|后天)?\d{1,2}:\d{2}",
        ),
    )
    title = text
    if time_text:
        title = title.replace(time_text, "")
    title = re.sub(r"^(帮我|给我|记录|创建|新增|添加|提醒我)", "", title).strip()
    title = title or "日程"

    arguments = {"title": title}
    if time_text:
        arguments["time_text"] = time_text
    return arguments


def _extract_phone_dial_arguments(raw_text: str) -> dict[str, str]:
    match = re.search(r"\+?\d[\d\s-]{5,}\d", raw_text)
    if not match:
        return {}
    return {"phone_number": re.sub(r"[^\d+]", "", match.group(0))}


def _extract_sms_compose_arguments(raw_text: str) -> dict[str, str]:
    message = re.sub(r"^\s*(发短信|发信息|发消息|短信)", "", raw_text).strip()
    return {"message_text": message} if message else {}


def _extract_app_open_arguments(raw_text: str) -> dict[str, str]:
    app_packages = {
        "淘宝": "com.taobao.taobao",
        "微信": "com.tencent.mm",
        "抖音": "com.ss.android.ugc.aweme",
        "支付宝": "com.eg.android.AlipayGphone",
        "京东": "com.jingdong.app.mall",
        "美团": "com.sankuai.meituan",
        "哔哩哔哩": "tv.danmaku.bili",
        "B站": "tv.danmaku.bili",
        "小红书": "com.xingin.xhs",
    }
    normalized = _normalize_text(raw_text)
    for app_name, package_name in app_packages.items():
        if _normalize_text(app_name) in normalized:
            return {"app_name": app_name, "package_name": package_name}
    return {}


def _extract_app_search_arguments(raw_text: str) -> dict[str, str]:
    apps = {
        "淘宝": "https://s.taobao.com/search?q={query}",
        "京东": "https://search.jd.com/Search?keyword={query}",
    }
    for app_name, url_template in apps.items():
        match = re.search(fr"{app_name}搜索(.+)$", raw_text)
        if match:
            query = match.group(1).strip()
            return {"app_name": app_name, "query": query, "fallback_url_template": url_template}
    return {}


def _extract_app_deep_link_arguments(raw_text: str) -> dict[str, str]:
    match = re.search(r"发微信给(.+?)说(.+)$", raw_text)
    if match:
        return {
            "app_name": "微信",
            "contact_name": match.group(1).strip(),
            "message_text": match.group(2).strip(),
            "execution_hint": "requires_app_deep_link_or_accessibility",
        }
    return {"app_name": "微信", "execution_hint": "requires_app_deep_link_or_accessibility"}


def _extract_browser_open_url_arguments(raw_text: str) -> dict[str, str]:
    match = re.search(r"https?://[^\s，。]+", raw_text)
    return {"url": match.group(0)} if match else {}


def _extract_media_play_arguments(raw_text: str, normalized_text: str) -> dict[str, str]:
    media_type = "video" if any(marker in normalized_text for marker in ("视频", "电影")) else "audio"
    return {"media_type": media_type, "query": raw_text.strip()}


def _extract_memory_update_arguments(raw_text: str) -> dict[str, str]:
    text = raw_text.strip()
    patterns = (
        r"^(?:请你)?记住(.+)$",
        r"^以后你要记得(.+)$",
        r"^我的偏好是(.+)$",
        r"^(?:以后)?(?:不要|别)再?(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        content = match.group(1).strip(" ，。,.")
        if pattern.startswith("^(?:以后)?") and content:
            content = f"不要{content}"
        return {"memory_content": content} if content else {}
    return {"memory_content": text} if text else {}


def _first_match_text(text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ""


def _extract_create_song_arguments(raw_text: str, normalized_text: str) -> dict[str, str]:
    arguments = {
        "theme": raw_text.strip(),
        "language": "zh",
    }
    genre = _extract_genre(normalized_text)
    if genre:
        arguments["genre"] = genre
    vocal = _extract_vocal(normalized_text)
    if vocal:
        arguments["vocal"] = vocal
    return arguments


def _extract_genre(text: str) -> str:
    genres = {
        "lofi": ("lofi", "lo-fi"),
        "rap": ("说唱", "rap"),
        "folk": ("民谣",),
        "electronic": ("电子",),
        "rock": ("摇滚",),
    }
    for genre, markers in genres.items():
        if any(marker in text for marker in markers):
            return genre
    return ""


def _extract_vocal(text: str) -> str:
    if "女声" in text:
        return "female"
    if "男声" in text:
        return "male"
    if "童声" in text:
        return "child"
    return ""


def _normalize_text(text: str) -> str:
    return "".join(str(text or "").strip().lower().split())
