from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


CapabilityMode = Literal["chat", "scenario", "native_action", "server_action", "clarify", "reject"]


@dataclass(frozen=True)
class CapabilityConfig:
    id: str
    mode: CapabilityMode
    intent: str
    keywords: tuple[str, ...]
    confidence: float
    scenario_id: str = ""
    scenario_intent: str = ""
    requires_confirmation: bool = False
    arguments: dict[str, Any] = field(default_factory=dict)


def default_capability_configs() -> list[CapabilityConfig]:
    return [
        CapabilityConfig(
            id="music_creation.publish_work",
            mode="scenario",
            intent="publish_work",
            scenario_id="music_creation",
            scenario_intent="publish_work",
            keywords=("保存并发布", "发布作品", "发出去", "发布到作品页"),
            confidence=0.9,
            requires_confirmation=True,
        ),
        CapabilityConfig(
            id="music_creation.revise_song",
            mode="scenario",
            intent="revise_song",
            scenario_id="music_creation",
            scenario_intent="revise_song",
            keywords=("副歌", "改成", "调整", "慢一点", "快一点", "重新唱", "修改"),
            confidence=0.84,
        ),
        CapabilityConfig(
            id="native.open_page",
            mode="native_action",
            intent="open_page",
            keywords=("打开作品页", "去作品页", "查看作品", "打开创作页", "打开模板页"),
            confidence=0.85,
            arguments={"target": "work_detail"},
        ),
        CapabilityConfig(
            id="native.calendar.create_event",
            mode="native_action",
            intent="calendar.create_event",
            keywords=("开会", "会议", "日程", "记录", "提醒我", "今天", "明天", "后天", "上午", "下午", "晚上"),
            confidence=0.86,
            requires_confirmation=True,
            arguments={
                "android_action": "android.intent.action.INSERT",
                "android_data": "content://com.android.calendar/events",
            },
        ),
        CapabilityConfig(
            id="native.phone.dial",
            mode="native_action",
            intent="phone.dial",
            keywords=("打电话", "拨号", "呼叫"),
            confidence=0.9,
            requires_confirmation=True,
            arguments={"android_action": "android.intent.action.DIAL"},
        ),
        CapabilityConfig(
            id="native.sms.compose",
            mode="native_action",
            intent="sms.compose",
            keywords=("发短信", "发信息", "发消息", "短信"),
            confidence=0.85,
            requires_confirmation=True,
            arguments={"android_action": "android.intent.action.SENDTO"},
        ),
        CapabilityConfig(
            id="native.browser.open_url",
            mode="native_action",
            intent="browser.open_url",
            keywords=("http://", "https://", "打开网址", "打开链接", "浏览器打开"),
            confidence=0.86,
            arguments={"android_action": "android.intent.action.VIEW"},
        ),
        CapabilityConfig(
            id="native.app.search",
            mode="native_action",
            intent="app.search",
            keywords=("打开淘宝搜索", "淘宝搜索", "打开京东搜索", "京东搜索"),
            confidence=0.84,
            arguments={"android_action": "android.intent.action.VIEW"},
        ),
        CapabilityConfig(
            id="native.app.open_deep_link",
            mode="native_action",
            intent="app.open_deep_link",
            keywords=("发微信给", "微信发给", "微信给"),
            confidence=0.8,
            requires_confirmation=True,
            arguments={"android_launcher": "app_deep_link_or_accessibility"},
        ),
        CapabilityConfig(
            id="native.gallery.pick_image",
            mode="native_action",
            intent="gallery.pick_image",
            keywords=("选一张图片", "选择图片", "选图片", "打开相册", "从相册"),
            confidence=0.84,
            arguments={
                "android_action": "android.intent.action.PICK",
                "media_type": "image",
            },
        ),
        CapabilityConfig(
            id="native.media.play_from_search",
            mode="native_action",
            intent="media.play_from_search",
            keywords=("看视频", "播放视频", "看电影", "播放音乐", "听歌"),
            confidence=0.82,
            arguments={"android_action": "android.media.action.MEDIA_PLAY_FROM_SEARCH"},
        ),
        CapabilityConfig(
            id="native.settings.open_wifi",
            mode="native_action",
            intent="settings.open_wifi",
            keywords=("wi-fi", "wifi", "无线网络", "打开 wi-fi 设置", "打开 wifi 设置"),
            confidence=0.87,
            arguments={
                "android_action": "android.settings.WIFI_SETTINGS",
                "panel": "wifi",
            },
        ),
        CapabilityConfig(
            id="native.camera.capture_photo",
            mode="native_action",
            intent="camera.capture_photo",
            keywords=("拍照", "拍张照片", "拍一张照片", "照相"),
            confidence=0.88,
            arguments={
                "android_action": "android.media.action.IMAGE_CAPTURE",
                "media_type": "image",
            },
        ),
        CapabilityConfig(
            id="native.camera.capture_video",
            mode="native_action",
            intent="camera.capture_video",
            keywords=("录视频", "录个视频", "拍视频", "录像"),
            confidence=0.88,
            arguments={
                "android_action": "android.media.action.VIDEO_CAPTURE",
                "media_type": "video",
            },
        ),
        CapabilityConfig(
            id="native.app.open",
            mode="native_action",
            intent="app.open",
            keywords=(
                "打开淘宝",
                "打开微信",
                "打开抖音",
                "打开支付宝",
                "打开京东",
                "打开美团",
                "打开哔哩哔哩",
                "打开b站",
                "打开小红书",
            ),
            confidence=0.83,
            arguments={"android_launcher": "getLaunchIntentForPackage"},
        ),
        CapabilityConfig(
            id="music_creation.create_song",
            mode="scenario",
            intent="create_song",
            scenario_id="music_creation",
            scenario_intent="create_song",
            keywords=("做一首", "生成一首", "写一首", "创作一首", "来一首", "做歌", "写歌"),
            confidence=0.88,
        ),
        CapabilityConfig(
            id="chat.general",
            mode="chat",
            intent="general",
            keywords=(),
            confidence=0.45,
        ),
    ]
