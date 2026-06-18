from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentProfileConfig:
    id: str
    name: str
    description: str
    voice_profile_id: str
    enabled_capability_ids: tuple[str, ...]
    routing_policy: dict[str, Any] = field(default_factory=dict)
    safety_policy: dict[str, Any] = field(default_factory=dict)


def default_agent_profile_configs() -> list[AgentProfileConfig]:
    return [
        AgentProfileConfig(
            id="default",
            name="默认助手",
            description="默认语音入口，启用基础聊天、页面打开和音乐创作能力。",
            voice_profile_id="default",
            enabled_capability_ids=(
                "native.open_page",
                "music_creation.create_song",
                "music_creation.revise_song",
                "music_creation.publish_work",
                "chat.general",
            ),
            routing_policy={"fallback_mode": "chat"},
            safety_policy={"confirm_risk_level": "high"},
        ),
        AgentProfileConfig(
            id="phone-assistant",
            name="手机助理",
            description="面向手机操作的工具型助手，启用第一批 Android-style 系统 Intent 能力。",
            voice_profile_id="short-latency",
            enabled_capability_ids=(
                "native.open_page",
                "native.calendar.create_event",
                "native.phone.dial",
                "native.sms.compose",
                "native.app.open",
                "native.app.search",
                "native.app.open_deep_link",
                "native.browser.open_url",
                "native.gallery.pick_image",
                "native.media.play_from_search",
                "native.settings.open_wifi",
                "native.camera.capture_photo",
                "native.camera.capture_video",
                "chat.general",
            ),
            routing_policy={"fallback_mode": "chat"},
            safety_policy={"confirm_risk_level": "high"},
        ),
    ]
