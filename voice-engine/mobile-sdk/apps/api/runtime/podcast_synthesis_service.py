from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

import websockets

from ..config import get_volc_podcast_headers, get_volc_podcast_ws_url, has_volc_podcast_credentials
from ..integrations.volc.events import CLIENT_EVENTS, SERVER_EVENTS
from ..integrations.volc.frames import ServerFrame, make_json_frame, parse_server_frame
from .podcast_service import PODCAST_AUDIO_MIME, PODCAST_AUDIO_VERSION


DEFAULT_PODCAST_SYNTHESIS_TIMEOUT_SECONDS = 240
PODCAST_COMPLETION_GRACE_SECONDS = 2.0


@dataclass
class PodcastSynthesisState:
    session_started: bool = False
    session_finished: bool = False
    connection_finished: bool = False
    podcast_ended: bool = False
    audio_url: str | None = None
    audio_chunks: list[bytes] = field(default_factory=list)
    chapters: list[dict[str, Any]] = field(default_factory=list)
    usage: Any = None
    input_metrics: Any = None
    warnings: list[str] = field(default_factory=list)
    _chapters_by_idx: dict[str, dict[str, Any]] = field(default_factory=dict)


async def request_podcast_audio(payload: dict[str, Any]) -> dict[str, Any]:
    if not has_volc_podcast_credentials():
        raise ValueError("缺少火山播客 API 配置。")

    try:
        state = await asyncio.wait_for(_request_podcast_audio(payload), timeout=_podcast_synthesis_timeout_seconds())
    except TimeoutError as exc:
        raise ValueError("火山播客音频合成超时，请减少轮次或稍后再试。") from exc

    return build_podcast_audio_result(payload, state)


def build_podcast_audio_result(payload: dict[str, Any], state: PodcastSynthesisState) -> dict[str, Any]:
    audio_url = state.audio_url
    warnings = list(state.warnings)

    if not audio_url and state.audio_chunks:
        audio_url = _audio_data_url(b"".join(state.audio_chunks))
        warnings.append("火山播客未返回 audio_url，已使用流式音频帧生成 data URL。")

    if not audio_url:
        if state.podcast_ended:
            raise ValueError("火山播客合成完成，但没有返回音频链接或音频帧。")
        if state.session_started:
            raise ValueError("火山播客会话已结束，但没有返回音频。")
        raise ValueError("火山播客连接已关闭。")

    return {
        "version": PODCAST_AUDIO_VERSION,
        "status": "ready",
        "audioUrl": audio_url,
        "payload": payload,
        "chapters": state.chapters,
        "usage": state.usage,
        "inputMetrics": state.input_metrics,
        "warnings": warnings,
    }


def consume_podcast_frame(state: PodcastSynthesisState, frame: ServerFrame) -> None:
    if frame.message_type == 0x0F:
        raise ValueError(_error_text(frame.payload, f"火山播客 API 返回错误{'：' + str(frame.code) if frame.code else ''}"))

    if frame.event in (SERVER_EVENTS["CONNECTION_FAILED"], SERVER_EVENTS["SESSION_FAILED"]):
        raise ValueError(_error_text(frame.payload, "火山播客连接失败。"))

    if frame.event == SERVER_EVENTS["SESSION_STARTED"]:
        state.session_started = True
        return

    if frame.event == SERVER_EVENTS["SESSION_FINISHED"]:
        state.session_finished = True
        return

    if frame.event == SERVER_EVENTS["CONNECTION_FINISHED"]:
        state.connection_finished = True
        return

    if frame.event == SERVER_EVENTS["PODCAST_ROUND_START"]:
        _merge_chapter(state, _chapter_from_payload(frame.payload))
        return

    if frame.event == SERVER_EVENTS["PODCAST_ROUND_RESPONSE"]:
        audio = _extract_audio_bytes(frame.payload)
        if audio:
            state.audio_chunks.append(audio)
        return

    if frame.event == SERVER_EVENTS["PODCAST_ROUND_END"]:
        _merge_chapter(state, _chapter_from_payload(frame.payload))
        return

    if frame.event == SERVER_EVENTS["PODCAST_END"]:
        state.podcast_ended = True
        payload = _as_dict(frame.payload)
        audio_url = _extract_audio_url(payload)
        if audio_url:
            state.audio_url = audio_url
        if isinstance(payload, dict):
            metrics = _first_value(payload, "input_metrics", "inputMetrics")
            if metrics is not None:
                state.input_metrics = metrics
        return

    if frame.event == SERVER_EVENTS["USAGE_RESPONSE"]:
        payload = frame.payload
        state.usage = payload.get("usage") if isinstance(payload, dict) and "usage" in payload else payload


async def _request_podcast_audio(payload: dict[str, Any]) -> PodcastSynthesisState:
    connect_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    state = PodcastSynthesisState()
    session_started_sent = False

    async with websockets.connect(
        get_volc_podcast_ws_url(),
        additional_headers=get_volc_podcast_headers(connect_id),
    ) as upstream:
        async def send_session_start() -> None:
            nonlocal session_started_sent
            if session_started_sent:
                return
            session_started_sent = True
            await upstream.send(make_json_frame(CLIENT_EVENTS["START_SESSION"], payload, session_id))

        await upstream.send(make_json_frame(CLIENT_EVENTS["START_CONNECTION"], {}))
        delayed_start = asyncio.create_task(_delayed(0.6, send_session_start))

        try:
            while True:
                timeout = PODCAST_COMPLETION_GRACE_SECONDS if state.podcast_ended and _has_audio(state) else None
                try:
                    data = await asyncio.wait_for(upstream.recv(), timeout=timeout)
                except TimeoutError:
                    if state.podcast_ended and _has_audio(state):
                        break
                    raise

                frame = parse_server_frame(data)
                if not frame:
                    continue

                if frame.event == SERVER_EVENTS["CONNECTION_STARTED"]:
                    await send_session_start()
                    continue

                consume_podcast_frame(state, frame)

                if frame.event == SERVER_EVENTS["SESSION_FINISHED"]:
                    await _try_send(upstream, make_json_frame(CLIENT_EVENTS["FINISH_CONNECTION"], {}))
                    continue

                if state.connection_finished:
                    break
        finally:
            delayed_start.cancel()

    return state


async def _try_send(upstream: Any, data: bytes) -> None:
    try:
        await upstream.send(data)
    except Exception:
        return


async def _delayed(seconds: float, callback) -> None:
    await asyncio.sleep(seconds)
    await callback()


def _has_audio(state: PodcastSynthesisState) -> bool:
    return bool(state.audio_url or state.audio_chunks)


def _audio_data_url(audio: bytes) -> str:
    return f"data:{PODCAST_AUDIO_MIME};base64,{base64.b64encode(audio).decode('ascii')}"


def _extract_audio_bytes(payload: Any) -> bytes | None:
    if isinstance(payload, bytes):
        return payload
    if not isinstance(payload, dict):
        return None

    for key in ("audio", "data", "chunk", "audio_data", "audioData"):
        value = payload.get(key)
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            try:
                raw = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
                return base64.b64decode(raw, validate=not value.startswith("data:"))
            except Exception:
                continue
    return None


def _extract_audio_url(payload: Any) -> str | None:
    payload = _as_dict(payload)
    if not isinstance(payload, dict):
        return None

    for key in ("audio_url", "audioUrl", "url"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    meta_info = _as_dict(_first_value(payload, "meta_info", "metaInfo"))
    if isinstance(meta_info, dict):
        for key in ("audio_url", "audioUrl", "url"):
            value = meta_info.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _chapter_from_payload(payload: Any) -> dict[str, Any] | None:
    payload = _as_dict(payload)
    if not isinstance(payload, dict):
        return None

    chapter = {
        "idx": _first_value(payload, "idx", "index", "round_idx", "roundIndex"),
        "speaker": _first_value(payload, "speaker", "speaker_id", "speakerId"),
        "text": _first_value(payload, "text", "content"),
        "startTime": _first_value(payload, "start_time", "startTime"),
        "endTime": _first_value(payload, "end_time", "endTime"),
        "audioDuration": _first_value(payload, "audio_duration", "audioDuration"),
    }
    return {key: value for key, value in chapter.items() if value is not None}


def _merge_chapter(state: PodcastSynthesisState, chapter: dict[str, Any] | None) -> None:
    if not chapter:
        return

    idx = chapter.get("idx")
    if idx is None:
        state.chapters.append(chapter)
        return

    key = str(idx)
    if key not in state._chapters_by_idx:
        state._chapters_by_idx[key] = chapter
        state.chapters.append(chapter)
        return

    state._chapters_by_idx[key].update(chapter)


def _first_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return None


def _as_dict(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return parsed
    return value


def _error_text(payload: Any, fallback: str) -> str:
    payload = _as_dict(payload)
    if isinstance(payload, dict):
        for key in ("error", "message", "error_message", "errorMessage"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(payload, str) and payload.strip():
        message = payload.strip()
        if "resource ID is mismatched with speaker related resource" in message:
            return (
                "火山播客音色与当前 Resource/App 授权不匹配：请配置 VOLC_PODCAST_SPEAKER_MAP "
                "或 VOLC_PODCAST_SPEAKER_MIZI 等环境变量，映射到播客服务已授权的真实 speaker ID。"
            )
        return message
    return fallback


def _podcast_synthesis_timeout_seconds() -> float:
    raw_value = os.environ.get("VOLC_PODCAST_TIMEOUT_SECONDS")
    if not raw_value:
        return DEFAULT_PODCAST_SYNTHESIS_TIMEOUT_SECONDS
    try:
        return min(max(float(raw_value), 10), 600)
    except ValueError:
        return DEFAULT_PODCAST_SYNTHESIS_TIMEOUT_SECONDS
