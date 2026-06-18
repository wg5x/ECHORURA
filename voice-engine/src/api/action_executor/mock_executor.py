from __future__ import annotations

from typing import Any


ActionResult = dict[str, Any]


def execute_mock_action(route_decision: dict[str, Any]) -> ActionResult:
    mode = str(route_decision.get("mode") or "")
    intent = str(route_decision.get("intent") or route_decision.get("scenario_intent") or "unknown")
    arguments = route_decision.get("arguments") if isinstance(route_decision.get("arguments"), dict) else {}

    result = {
        "type": "action_result",
        "result_type": "native_action_result" if mode == "native_action" else "noop",
        "session_id": route_decision.get("session_id"),
        "turn_id": route_decision.get("turn_id"),
        "agent_profile_id": route_decision.get("agent_profile_id"),
        "mode": mode,
        "intent": intent,
        "status": "mocked" if mode == "native_action" else "skipped",
        "summary": _summary_for_intent(intent, arguments),
        "requires_confirmation": bool(route_decision.get("requires_confirmation")),
        "requires_native_bridge": _requires_native_bridge(intent, arguments),
        "arguments": arguments,
    }
    return result


def _summary_for_intent(intent: str, arguments: dict[str, Any]) -> str:
    if intent == "calendar.create_event":
        title = str(arguments.get("title") or "日程")
        time_text = str(arguments.get("time_text") or "").strip()
        return f"准备创建日程：{time_text} {title}".strip()
    if intent == "phone.dial":
        return f"准备拨号 {arguments.get('phone_number') or ''}".strip()
    if intent == "sms.compose":
        message = str(arguments.get("message_text") or "").strip()
        return f"准备发送短信：{message}" if message else "准备发送短信"
    if intent == "app.open":
        return f"准备打开{arguments.get('app_name') or '应用'}"
    if intent == "app.search":
        app_name = str(arguments.get("app_name") or "应用")
        query = str(arguments.get("query") or "").strip()
        return f"准备在{app_name}搜索：{query}" if query else f"准备在{app_name}搜索"
    if intent == "app.open_deep_link":
        app_name = str(arguments.get("app_name") or "应用")
        contact_name = str(arguments.get("contact_name") or "").strip()
        message_text = str(arguments.get("message_text") or "").strip()
        if contact_name and message_text:
            return f"准备通过{app_name}给{contact_name}发送：{message_text}"
        return f"准备打开{app_name}内动作"
    if intent == "browser.open_url":
        return f"准备打开链接 {arguments.get('url') or ''}".strip()
    if intent == "gallery.pick_image":
        return "准备打开相册选择图片"
    if intent == "media.play_from_search":
        media_type = "视频" if arguments.get("media_type") == "video" else "音频"
        query = str(arguments.get("query") or "").strip()
        return f"准备播放{media_type}：{query}" if query else f"准备播放{media_type}"
    if intent == "settings.open_wifi":
        return "准备打开 Wi-Fi 设置"
    if intent == "camera.capture_photo":
        return "准备打开相机拍照"
    if intent == "camera.capture_video":
        return "准备打开相机录像"
    if intent == "open_page":
        return f"准备打开页面：{arguments.get('target') or 'unknown'}"
    return "当前路由结果不需要执行原生动作。"


def _requires_native_bridge(intent: str, arguments: dict[str, Any]) -> bool:
    if intent == "app.open_deep_link":
        return True
    if arguments.get("android_action") or arguments.get("android_launcher"):
        return False
    return False
