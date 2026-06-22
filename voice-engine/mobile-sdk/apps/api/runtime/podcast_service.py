from __future__ import annotations

import json
import os
import re
from typing import Any

from ..shared.value_utils import to_int_in_range, to_string_value


PODCAST_DRAFT_VERSION = "local-podcast-draft-v1"
MAX_ROUND_CHARS = 260
MAX_DRAFT_SOURCE_CHARS = 12000
MAX_PODCAST_TOTAL_CHARS = 9500
PODCAST_AUDIO_VERSION = "volc-podcast-audio-v1"
PODCAST_AUDIO_MIME = "audio/mpeg"
PODCAST_HOSTS = {
    "mizi": "黑猫侦探社咪仔",
    "dayi": "大壹先生",
    "liufei": "刘飞",
    "xiaolei": "潇磊",
}
DEFAULT_PODCAST_SPEAKERS = {
    "mizi": "zh_female_mizaitongxue_v2_saturn_bigtts",
    "dayi": "zh_male_dayixiansheng_v2_saturn_bigtts",
    "liufei": "zh_male_liufei_v2_saturn_bigtts",
    "xiaolei": "zh_male_xiaolei_v2_saturn_bigtts",
}


def build_podcast_draft(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("播客草稿请求不能为空。")

    topic = _compact(value.get("topic") or value.get("title") or value.get("prompt"), 80)
    raw_source_text = to_string_value(value.get("sourceText") or value.get("content") or _report_summary(value.get("report")))
    source_text = _compact(raw_source_text, MAX_DRAFT_SOURCE_CHARS)
    duration_minutes = to_int_in_range(value.get("durationMinutes"), 6, 2, 20)
    warnings: list[str] = []

    if not topic and source_text:
        topic = source_text[:36]
    if not topic:
        topic = "未命名话题"
        warnings.append("缺少明确话题，已生成通用播客草稿。")
    if not source_text:
        warnings.append("缺少来源材料，草稿只会围绕话题做结构化展开。")
    if len(re.sub(r"\s+", " ", raw_source_text).strip()) > len(source_text):
        warnings.append(f"来源材料较长，已截取前 {MAX_DRAFT_SOURCE_CHARS} 字生成草稿。")

    source_summary = _source_summary(source_text, topic)
    rounds = _build_rounds(topic, source_summary, source_text, duration_minutes)

    return {
        "version": PODCAST_DRAFT_VERSION,
        "title": f"{topic}｜双人解读",
        "format": "duo_brief",
        "durationMinutes": duration_minutes,
        "sourceSummary": source_summary,
        "rounds": rounds,
        "synthesis": {
            "provider": "volc_podcast",
            "recommendedAction": 3,
            "maxRoundChars": MAX_ROUND_CHARS,
            "readyForReview": True,
        },
        "warnings": warnings,
    }


def build_podcast_audio_request(value: Any, *, configured: bool) -> dict[str, Any]:
    payload = build_podcast_audio_payload(value)

    if configured:
        return {
            "version": PODCAST_AUDIO_VERSION,
            "status": "ready",
            "audioUrl": None,
            "payload": payload,
            "warnings": ["火山播客 API 已配置，真实合成会通过 WebSocket v3 执行。"],
        }

    return {
        "version": PODCAST_AUDIO_VERSION,
        "status": "needs_config",
        "audioUrl": None,
        "payload": payload,
        "warnings": ["缺少火山播客 API 配置，已生成 action=3 请求参数，但未发起真实合成。"],
    }


def build_podcast_audio_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("播客音频请求不能为空。")

    rounds = _normalize_rounds(value.get("rounds"))
    host_a = _normalize_podcast_host(value.get("hostA"), "mizi")
    host_b = _normalize_podcast_host(value.get("hostB"), "dayi")
    speaker_a = _resolve_podcast_speaker(host_a)
    speaker_b = _resolve_podcast_speaker(host_b)
    if host_a == host_b or speaker_a == speaker_b:
        raise ValueError("两位播客主持人不能使用同一个音色。")

    payload = {
        "action": 3,
        "input_info": {
            "return_audio_url": True,
        },
        "audio_config": {
            "format": "mp3",
            "sample_rate": 24000,
        },
        "speaker_info": {
            "speakers": [speaker_a, speaker_b],
        },
        "nlp_texts": [
            {
                "idx": round_item["idx"],
                "speaker": speaker_a if round_item["speaker"] == "host_a" else speaker_b,
                "text": round_item["text"],
            }
            for round_item in rounds
        ],
    }
    return payload


def _build_rounds(topic: str, source_summary: str, source_text: str, duration_minutes: int) -> list[dict[str, Any]]:
    target_rounds = _target_round_count(duration_minutes, source_text)
    content_slots = max(1, target_rounds - 3)
    chunks = _source_chunks(source_text, content_slots)
    if not chunks:
        chunks = [source_summary]

    rows: list[tuple[str, str]] = [
        ("host_a", f"今天我们做一期「{topic}」的双人解读，先给结论，再按材料里的重点逐段拆开。"),
        ("host_b", f"先交代材料脉络：{source_summary}"),
    ]
    templates = [
        "第{idx}个重点是：{chunk}",
        "我把这一段翻成更好听的话：{chunk}",
        "这里值得停一下，材料实际在强调：{chunk}",
        "如果从听众视角理解，这一段的关键信息是：{chunk}",
        "再往下看，新的线索是：{chunk}",
        "这一点可以和前面连起来：{chunk}",
    ]

    for index, chunk in enumerate(chunks):
        speaker = "host_a" if index % 2 == 0 else "host_b"
        template = templates[index % len(templates)]
        rows.append((speaker, template.format(idx=index + 1, chunk=chunk)))

    rows.append(("host_b", "收束一下：这期内容适合先人工审核脚本，再进入音频合成，避免信息多的时候听感流畅但事实跑偏。"))

    rounds = [
        {"idx": idx + 1, "speaker": speaker, "text": _compact(text, MAX_ROUND_CHARS)}
        for idx, (speaker, text) in enumerate(rows[:target_rounds])
    ]
    return _trim_rounds_to_total_limit(rounds)


def _source_summary(text: str, topic: str) -> str:
    if not text:
        return f"当前只有话题「{topic}」，还没有额外来源。"
    sentences = _split_source_units(text)
    return _compact("；".join(sentences[:3]), MAX_ROUND_CHARS)


def _target_round_count(duration_minutes: int, source_text: str) -> int:
    if not source_text:
        return 5
    material_units = len(_split_source_units(source_text))
    duration_target = max(8, min(36, duration_minutes * 4))
    material_target = max(8, min(36, material_units + 4))
    return min(duration_target, material_target)


def _source_chunks(text: str, desired_count: int) -> list[str]:
    units = _split_source_units(text)
    if not units:
        return []
    if len(units) <= desired_count:
        return [_compact(unit, 190) for unit in units]

    chunks: list[str] = []
    total_units = len(units)
    for index in range(desired_count):
        start = index * total_units // desired_count
        end = (index + 1) * total_units // desired_count
        chunk_units = units[start : max(start + 1, end)]
        chunks.append(_compact("；".join(chunk_units), 190))
    return chunks


def _split_source_units(text: str) -> list[str]:
    cleaned = re.sub(r"[#>*`]+", " ", text)
    units = [re.sub(r"\s+", " ", item).strip() for item in re.split(r"[。！？!?；;\n]+", cleaned) if item.strip()]
    result: list[str] = []
    for unit in units:
        if len(unit) <= 220:
            result.append(unit)
            continue
        result.extend(_compact(unit[index : index + 180], 180) for index in range(0, len(unit), 180))
    return [unit for unit in result if unit]


def _trim_rounds_to_total_limit(rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = 0
    trimmed: list[dict[str, Any]] = []
    for round_item in rounds:
        remaining = MAX_PODCAST_TOTAL_CHARS - total
        if remaining <= 0:
            break
        text = _compact(round_item["text"], min(MAX_ROUND_CHARS, remaining))
        if not text:
            break
        trimmed.append({**round_item, "idx": len(trimmed) + 1, "text": text})
        total += len(text)
    return trimmed


def _report_summary(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    transcript = value.get("transcript") if isinstance(value.get("transcript"), list) else []
    turns = [
        _compact(item.get("text"), 80)
        for item in transcript
        if isinstance(item, dict) and item.get("role") == "user" and _compact(item.get("text"), 80)
    ]
    return _compact(value.get("summary") or "；".join(turns[-3:]), 900)


def _compact(value: Any, limit: int) -> str:
    return re.sub(r"\s+", " ", to_string_value(value)).strip()[:limit]


def _normalize_rounds(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("播客轮次不能为空。")

    rounds: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        speaker = to_string_value(item.get("speaker"))
        text = _compact(item.get("text"), 300)
        if speaker not in {"host_a", "host_b"} or not text:
            continue
        rounds.append({"idx": to_int_in_range(item.get("idx"), index + 1, 1, 200), "speaker": speaker, "text": text})

    if not rounds:
        raise ValueError("播客轮次不能为空。")
    if sum(len(round_item["text"]) for round_item in rounds) > 10000:
        raise ValueError("播客轮次总文本不能超过 10000 字符。")
    return rounds


def _normalize_podcast_host(value: Any, fallback: str) -> str:
    host = to_string_value(value) or fallback
    if host not in PODCAST_HOSTS:
        raise ValueError("播客主持人音色无效。")
    return host


def _resolve_podcast_speaker(host: str) -> str:
    mapped = to_string_value(os.environ.get(f"VOLC_PODCAST_SPEAKER_{host.upper()}"))
    if mapped:
        return mapped

    raw_map = os.environ.get("VOLC_PODCAST_SPEAKER_MAP")
    if raw_map:
        try:
            speaker_map = json.loads(raw_map)
        except json.JSONDecodeError:
            speaker_map = {}
        if isinstance(speaker_map, dict):
            mapped = to_string_value(speaker_map.get(host))
            if mapped:
                return mapped

    return DEFAULT_PODCAST_SPEAKERS.get(host, host)
