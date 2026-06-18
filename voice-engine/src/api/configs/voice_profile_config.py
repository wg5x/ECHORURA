from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_O2_SPEAKER = "zh_female_vv_jupiter_bigtts"
DEFAULT_SC2_SPEAKER = "saturn_zh_female_aojiaonvyou_tob"

O2_SPEAKERS = {
    "zh_female_vv_jupiter_bigtts",
    "zh_female_xiaohe_jupiter_bigtts",
    "zh_male_yunzhou_jupiter_bigtts",
    "zh_male_xiaotian_jupiter_bigtts",
}

SC2_SPEAKERS = {
    "saturn_zh_female_aojiaonvyou_tob",
    "saturn_zh_female_bingjiaojiejie_tob",
    "saturn_zh_female_chengshujiejie_tob",
    "saturn_zh_female_keainvsheng_tob",
    "saturn_zh_female_nuanxinxuejie_tob",
    "saturn_zh_female_tiexinnvyou_tob",
    "saturn_zh_female_wenrouwenya_tob",
    "saturn_zh_female_wumeiyujie_tob",
    "saturn_zh_female_xingganyujie_tob",
    "saturn_zh_male_aiqilingren_tob",
    "saturn_zh_male_aojiaogongzi_tob",
    "saturn_zh_male_aojiaojingying_tob",
    "saturn_zh_male_aomanshaoye_tob",
    "saturn_zh_male_badaoshaoye_tob",
    "saturn_zh_male_bingjiaobailian_tob",
    "saturn_zh_male_bujiqingnian_tob",
    "saturn_zh_male_chengshuzongcai_tob",
    "saturn_zh_male_cixingnansang_tob",
    "saturn_zh_male_cujingnanyou_tob",
    "saturn_zh_male_fengfashaonian_tob",
    "saturn_zh_male_fuheigongzi_tob",
    "en_male_tim_uranus_bigtts",
    "en_female_dacey_uranus_bigtts",
    "en_female_stokie_uranus_bigtts",
}


@dataclass(frozen=True)
class VoiceProfileConfig:
    id: str
    name: str
    description: str
    config: dict[str, Any]


def default_realtime_config() -> dict[str, Any]:
    return {
        "mode": "o2",
        "botName": "ECHORURA",
        "speaker": DEFAULT_O2_SPEAKER,
        "systemRole": "你是 ECHORURA 的语音入口助手。先用简短中文自然对话，支持唱歌请求和联网搜索。",
        "speakingStyle": "表达自然、简短、友好。优先一句话回答。",
        "openingLine": "你好，我是 ECHORURA。我们先测试实时语音对话。",
        "strictAudit": True,
        "enableWebSearch": True,
        "enableMusic": True,
        "enableLoudnessNorm": False,
        "enableConversationTruncate": True,
        "enableUserQueryExit": True,
        "speechRate": 0,
        "loudnessRate": 0,
    }


def default_voice_profile_configs() -> list[VoiceProfileConfig]:
    default_config = default_realtime_config()
    return [
        VoiceProfileConfig(
            id="default",
            name="默认语音",
            description="自然、简短，保留联网和唱歌能力。",
            config={
                **default_config,
                "openingLine": "你好，我是 ECHORURA。你可以和我语音对话，也可以让我唱歌或联网搜索。",
            },
        ),
        VoiceProfileConfig(
            id="short-latency",
            name="短回答测试",
            description="更短回复，用于测试延迟和连续对话。",
            config={
                **default_config,
                "speakingStyle": "表达自然、非常简短。优先半句话到一句话回答，不主动展开。",
                "openingLine": "你好，我会用更短的回答陪你测试实时语音。",
            },
        ),
        VoiceProfileConfig(
            id="music-test",
            name="音乐测试",
            description="偏音乐请求，用于测试唱歌和歌曲相关回复。",
            config={
                **default_config,
                "systemRole": "你是 ECHORURA 的音乐语音入口助手。优先理解唱歌、歌曲、风格和情绪相关请求，也可以自然闲聊。",
                "speakingStyle": "表达自然、简短，有音乐陪伴感。遇到唱歌或歌曲请求时先确认并直接响应。",
                "openingLine": "你好，我是 ECHORURA。你可以让我唱歌，也可以说想听的风格或情绪。",
            },
        ),
    ]
