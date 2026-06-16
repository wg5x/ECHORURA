from __future__ import annotations

import os
from typing import Any

from ...shared.value_utils import to_bool, to_int_in_range, to_string_value


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


def default_realtime_config() -> dict[str, Any]:
    return {
        "mode": "o2",
        "botName": "ECHORURA",
        "speaker": DEFAULT_O2_SPEAKER,
        "systemRole": "你是 ECHORURA 的语音入口助手。先用简短中文自然对话，帮助用户验证实时语音链路，不执行音乐创作业务动作。",
        "speakingStyle": "表达自然、简短、友好。优先一句话回答。",
        "openingLine": "你好，我是 ECHORURA。我们先测试实时语音对话。",
        "strictAudit": True,
        "enableWebSearch": False,
        "enableMusic": False,
        "enableLoudnessNorm": False,
        "enableConversationTruncate": True,
        "enableUserQueryExit": True,
        "speechRate": 0,
        "loudnessRate": 0,
    }


def build_start_session_payload(raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
    raw_config = {**default_realtime_config(), **(raw_config or {})}
    config = _normalize_config(raw_config)
    warnings: list[str] = []

    if not config["speaker"]:
        raise ValueError("音色不能为空，请选择或填写 speaker。")

    if config["mode"] == "o2" and config["speaker"] not in O2_SPEAKERS:
        warnings.append("当前音色不在端到端实时语音大模型 S2S-O 官方音色列表中，可能被火山 API 拒绝。")

    if config["mode"] == "sc2" and config["speaker"] not in SC2_SPEAKERS:
        warnings.append("当前音色不在端到端实时语音大模型 SC 2.0 官方音色列表中，可能被火山 API 拒绝。")

    if config["enableWebSearch"] and not os.environ.get("VOLC_WEBSEARCH_API_KEY"):
        warnings.append("已开启联网能力，但后端未配置 VOLC_WEBSEARCH_API_KEY；真实联网请求会被火山 API 拒绝。")

    dialog_extra = clean_object(
        {
            "strict_audit": config["strictAudit"],
            "enable_volc_websearch": config["enableWebSearch"],
            "volc_websearch_api_key": os.environ.get("VOLC_WEBSEARCH_API_KEY") if config["enableWebSearch"] else None,
            "input_mod": None,
            "enable_music": config["enableMusic"],
            "enable_loudness_norm": config["enableLoudnessNorm"],
            "enable_conversation_truncate": config["enableConversationTruncate"],
            "enable_user_query_exit": config["enableUserQueryExit"],
            "model": config["model"],
        }
    )

    if config["mode"] == "o2":
        dialog = {
            "bot_name": config["botName"],
            "system_role": config["systemRole"],
            "speaking_style": config["speakingStyle"],
            "dialog_id": "",
            "extra": dialog_extra,
        }
    else:
        dialog = {
            "character_manifest": config["characterManifest"],
            "dialog_id": "",
            "extra": dialog_extra,
        }

    payload = {
        "asr": {"extra": {}},
        "tts": {
            "speaker": config["speaker"],
            "extra": clean_object(
                {
                    "explicit_dialect": config["explicitDialect"],
                    "tts_2.0_model": "expressive"
                    if config["speaker"].startswith("S_") or config["speaker"].startswith("saturn_")
                    else "",
                }
            ),
            "audio_config": clean_object(
                {
                    "channel": 1,
                    "format": "pcm_s16le",
                    "sample_rate": 24000,
                    "speech_rate": config["speechRate"],
                    "loudness_rate": config["loudnessRate"],
                }
            ),
        },
        "dialog": clean_object(dialog),
    }

    return {"config": config, "payload": payload, "warnings": warnings}


def redact_payload(value: Any) -> Any:
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if not isinstance(value, dict):
        return value

    result: dict[str, Any] = {}
    for key, entry in value.items():
        if any(token in key.lower() for token in ("key", "token", "secret")) and entry:
            result[key] = "<redacted>"
        else:
            result[key] = redact_payload(entry)
    return result


def clean_object(value: Any) -> Any:
    if isinstance(value, list):
        return [clean_object(item) for item in value]
    if not isinstance(value, dict):
        return value

    result: dict[str, Any] = {}
    for key, entry in value.items():
        if entry is None or entry == "":
            continue
        if isinstance(entry, (dict, list)):
            next_value = clean_object(entry)
            if isinstance(next_value, list) or next_value:
                result[key] = next_value
            continue
        result[key] = entry
    return result


def _normalize_config(raw: dict[str, Any]) -> dict[str, Any]:
    mode = "sc2" if raw.get("mode") == "sc2" else "o2"
    selected_speaker = to_string_value(raw.get("speaker"), DEFAULT_O2_SPEAKER if mode == "o2" else DEFAULT_SC2_SPEAKER)
    custom_speaker = to_string_value(raw.get("customSpeaker"))
    speaker = custom_speaker if selected_speaker == "custom" else selected_speaker

    return {
        "mode": mode,
        "model": "1.2.1.1" if mode == "o2" else "2.2.0.0",
        "speaker": speaker,
        "botName": to_string_value(raw.get("botName"), "ECHORURA")[:20],
        "systemRole": to_string_value(raw.get("systemRole")),
        "speakingStyle": to_string_value(raw.get("speakingStyle")),
        "characterManifest": to_string_value(raw.get("characterManifest")),
        "openingLine": to_string_value(raw.get("openingLine")),
        "strictAudit": to_bool(raw.get("strictAudit"), True),
        "enableWebSearch": to_bool(raw.get("enableWebSearch")),
        "enableMusic": mode == "o2" and to_bool(raw.get("enableMusic")),
        "enableLoudnessNorm": to_bool(raw.get("enableLoudnessNorm")),
        "enableConversationTruncate": to_bool(raw.get("enableConversationTruncate"), True),
        "enableUserQueryExit": to_bool(raw.get("enableUserQueryExit"), True),
        "speechRate": to_int_in_range(raw.get("speechRate"), 0, -50, 100),
        "loudnessRate": to_int_in_range(raw.get("loudnessRate"), 0, -50, 100),
        "explicitDialect": raw.get("explicitDialect") if raw.get("explicitDialect") in {"dongbei", "sichuan", "shaanxi"} else "",
    }
