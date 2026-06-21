from __future__ import annotations

import asyncio
import base64
import json
import re
import time
import unicodedata
import uuid
from datetime import datetime
from typing import Any

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from ..config import (
    get_conversations_dir,
    get_debug_events_dir,
    get_memories_dir,
    get_recordings_dir,
    get_volc_headers,
    get_volc_ws_url,
    has_volc_credentials,
    is_realtime_debug_log_enabled,
    is_voice_recording_enabled,
)
from ..conversation_store import ConversationStore
from ..integrations.volc.events import CLIENT_EVENTS, SERVER_EVENTS
from ..integrations.volc.frames import ServerFrame, make_audio_frame, make_json_frame, parse_server_frame
from ..integrations.volc.payload import build_start_session_payload, redact_payload
from ..memory_store import LongTermMemoryStore
from ..semantic_router import SemanticRouter
from .debug_log import RealtimeDebugLogger
from .recording import LocalSessionRecorder


class RealtimeGateway:
    def __init__(self, client_ws: WebSocket) -> None:
        self.client_ws = client_ws
        self.upstream = None
        self.upstream_task: asyncio.Task | None = None
        self.delayed_start_task: asyncio.Task | None = None
        self.session_id = ""
        self.upstream_ready = False
        self.closing_upstream = False
        self.assistant_output_seq = 0
        self.current_assistant_output_id = ""
        self.current_assistant_text = ""
        self.chat_response_output_id = ""
        self.chat_response_text = ""
        self.user_output_seq = 0
        self.current_user_output_id = ""
        self.current_user_text = ""
        self.recorder: LocalSessionRecorder | None = None
        self.debug_logger: RealtimeDebugLogger | None = None
        self.conversation_store: ConversationStore | None = None
        self.memory_store = LongTermMemoryStore(get_memories_dir())
        self.memory_context: dict[str, Any] = {"memories": [], "system_role_text": ""}
        self.semantic_router = SemanticRouter()
        self.agent_profile_id = "default"
        self.session_started_at = 0.0
        self.first_output_audio_at = 0.0

    async def run(self) -> None:
        await self.client_ws.accept()
        try:
            while True:
                message = await self.client_ws.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                if message.get("bytes") is not None:
                    await self._handle_binary(message["bytes"])
                    continue
                if message.get("text") is not None:
                    await self._handle_text(message["text"])
        except WebSocketDisconnect:
            pass
        finally:
            await self._close_upstream()
            await self._cancel_tasks()
            self._close_recorder()

    async def _handle_binary(self, raw: bytes) -> None:
        if not self.upstream or not self.session_id:
            return
        try:
            if self.recorder:
                self.recorder.write_input(raw)
            if self.conversation_store:
                self.conversation_store.write_input_audio(raw)
            await self.upstream.send(make_audio_frame(CLIENT_EVENTS["TASK_REQUEST"], raw, self.session_id))
        except Exception:
            await self._send_json({"type": "error", "message": "发送音频到火山实时语音失败。"})

    async def _handle_text(self, raw: str) -> None:
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_json({"type": "error", "message": "无法解析客户端消息。"})
            return

        if message.get("type") == "start":
            await self._cancel_tasks()
            await self._close_upstream()
            self._set_agent_profile_from_message(message)
            if not has_volc_credentials():
                await self._send_json({"type": "error", "message": "缺少 VOLC_API_APP_ID 或 VOLC_API_ACCESS_KEY。"})
                await self._send_json({"type": "status", "status": "idle"})
                return

            try:
                memory_session_ids = _extract_memory_session_ids(message)
                self.memory_context = self.memory_store.build_memory_context(
                    self.agent_profile_id,
                    session_ids=memory_session_ids,
                )
                config = _inject_memory_context(message.get("config") or {}, self.memory_context)
                session = build_start_session_payload(config)
            except Exception as exc:
                await self._send_json({"type": "error", "message": str(exc) or "StartSession 配置无效。"})
                return

            await self._start_volc_session(session)
            return

        if message.get("type") == "user_text":
            text = str(message.get("text") or "").strip()
            if self.upstream and self.session_id and text:
                try:
                    await self.upstream.send(make_json_frame(CLIENT_EVENTS["CHAT_TEXT_QUERY"], {"content": text}, self.session_id))
                except Exception:
                    await self._send_json({"type": "error", "message": "发送文本到火山实时语音失败。"})
            return

        if message.get("type") == "finish":
            await self._finish()
            return

    async def _start_volc_session(self, session: dict[str, Any]) -> None:
        payload = session["payload"]
        warnings = session["warnings"]
        connect_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.upstream_ready = False
        self.closing_upstream = False
        self.assistant_output_seq = 0
        self.current_assistant_output_id = ""
        self.current_assistant_text = ""
        self.chat_response_output_id = ""
        self.chat_response_text = ""
        self.user_output_seq = 0
        self.current_user_output_id = ""
        self.current_user_text = ""
        self._close_recorder()
        self.debug_logger = RealtimeDebugLogger(is_realtime_debug_log_enabled(), get_debug_events_dir(), self.session_id)
        self.session_started_at = time.monotonic()
        self.first_output_audio_at = 0.0
        self.recorder = LocalSessionRecorder(is_voice_recording_enabled(), get_recordings_dir(), self.session_id)
        self.conversation_store = ConversationStore(
            base_dir=get_conversations_dir(),
            session_id=self.session_id,
            agent_profile_id=self.agent_profile_id,
            config=session["config"],
            memory_context=self.memory_context,
        )
        self._record_debug(
            "start_session",
            {
                "session_id": self.session_id,
                "payload": redact_payload(payload),
                "warnings": warnings,
                "config": session["config"],
            },
        )

        await self._send_json({"type": "payload", "payload": redact_payload(payload), "warnings": warnings})
        await self._send_json({"type": "status", "status": "connecting", "warnings": warnings})

        try:
            self.upstream = await websockets.connect(get_volc_ws_url(), additional_headers=get_volc_headers(connect_id))
            await self.upstream.send(make_json_frame(CLIENT_EVENTS["START_CONNECTION"], {}))
            self.delayed_start_task = asyncio.create_task(self._delayed_send_session_start(self.upstream, payload))
            self.upstream_task = asyncio.create_task(self._upstream_loop(self.upstream, payload, warnings, session["config"]))
        except Exception as exc:
            await self._send_json({"type": "error", "message": f"连接火山实时语音 WebSocket 失败：{exc}"})
            await self._send_json({"type": "status", "status": "idle", "warnings": warnings})

    async def _upstream_loop(self, upstream, payload: dict[str, Any], warnings: list[str], config: dict[str, Any]) -> None:
        try:
            async for data in upstream:
                if self.upstream is not upstream:
                    return
                frame = parse_server_frame(data)
                if not frame:
                    continue
                self._record_debug("upstream_frame", _make_upstream_debug_payload(frame))

                if frame.message_type == 0x0F:
                    error_text = frame.payload.get("error") if isinstance(frame.payload, dict) else None
                    message = error_text or f"火山 API 返回错误：{frame.code}"
                    self._record_debug("error", {"message": message, "code": frame.code, "event": frame.event})
                    await self._send_upstream_error(message)
                    continue

                if frame.event == SERVER_EVENTS["CONNECTION_STARTED"]:
                    await self._send_session_start(upstream, payload)
                    continue

                if frame.event in (SERVER_EVENTS["CONNECTION_FAILED"], SERVER_EVENTS["SESSION_FAILED"]):
                    error_text = frame.payload.get("error") if isinstance(frame.payload, dict) else None
                    message = error_text or "火山实时语音连接失败。"
                    self._record_debug("error", {"message": message, "code": frame.code, "event": frame.event})
                    await self._send_upstream_error(message)
                    continue

                if frame.event == SERVER_EVENTS["SESSION_STARTED"]:
                    await self._send_json({"type": "status", "status": "connected", "warnings": warnings})
                    if config.get("openingLine"):
                        await upstream.send(make_json_frame(CLIENT_EVENTS["SAY_HELLO"], {"content": config["openingLine"]}, self.session_id))
                    continue

                if frame.event == SERVER_EVENTS["ASR_RESPONSE"] and isinstance(frame.payload, dict):
                    text = _extract_asr_text(frame.payload)
                    if text:
                        self._reset_assistant_turn()
                        await self._handle_user_asr_text(text)
                    continue

                if frame.event == SERVER_EVENTS["ASR_ENDED"]:
                    self.current_user_output_id = ""
                    self.current_user_text = ""
                    continue

                if frame.event == SERVER_EVENTS["CHAT_RESPONSE"] and isinstance(frame.payload, dict) and frame.payload.get("content"):
                    await self._handle_chat_response_content(str(frame.payload["content"]))
                    continue

                if frame.event in (SERVER_EVENTS["TTS_SENTENCE_START"], SERVER_EVENTS["TTS_SENTENCE_END"]):
                    text = frame.payload.get("text") if isinstance(frame.payload, dict) else None
                    if text:
                        await self._handle_tts_sentence_text(str(text))
                    continue

                if frame.event == SERVER_EVENTS["TTS_RESPONSE"] and isinstance(frame.payload, bytes):
                    if self.recorder:
                        self.recorder.write_output(frame.payload)
                    if self.conversation_store:
                        self.conversation_store.write_output_audio(frame.payload)
                    if not self.first_output_audio_at:
                        self.first_output_audio_at = time.monotonic()
                        self._record_debug(
                            "audio_latency",
                            _make_audio_latency_debug_payload(
                                session_id=self.session_id,
                                session_started_at=self.session_started_at,
                                first_audio_at=self.first_output_audio_at,
                                payload_bytes=len(frame.payload),
                            ),
                        )
                    await self._send_json(
                        {
                            "type": "audio",
                            "mime": "audio/pcm; format=s16le; rate=24000",
                            "data": base64.b64encode(frame.payload).decode("ascii"),
                            "outputId": self.current_assistant_output_id or self._next_assistant_output_id(),
                        }
                    )
                    continue

                if frame.event in (SERVER_EVENTS["TTS_ENDED"], SERVER_EVENTS["CHAT_ENDED"]):
                    self.chat_response_output_id = ""
                    self.chat_response_text = ""
                    continue

                if frame.event == SERVER_EVENTS["USAGE_RESPONSE"] and isinstance(frame.payload, dict) and frame.payload.get("usage"):
                    await self._send_json({"type": "usage", "usage": frame.payload["usage"]})
                    continue

                if frame.event in (SERVER_EVENTS["SESSION_FINISHED"], SERVER_EVENTS["CONNECTION_FINISHED"]):
                    self._finalize_conversation()
                    self.session_id = ""
                    self.upstream_ready = False
                    await self._send_json({"type": "status", "status": "idle", "warnings": warnings})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if not self.closing_upstream:
                message = f"火山实时语音连接已中断：{exc}"
                self._record_debug("error", {"message": message})
                await self._send_json({"type": "error", "message": message})
                await self._send_json({"type": "status", "status": "idle", "warnings": warnings})
        finally:
            if self.upstream is upstream:
                self.upstream = None
            self._finalize_conversation()
            self.session_id = ""
            self.upstream_ready = False

    async def _send_session_start(self, upstream, payload: dict[str, Any]) -> None:
        if self.upstream is not upstream or self.upstream_ready or not self.session_id:
            return
        self.upstream_ready = True
        await upstream.send(make_json_frame(CLIENT_EVENTS["START_SESSION"], payload, self.session_id))

    async def _send_upstream_error(self, message: str) -> None:
        display_message = _normalize_upstream_error_message(message)
        await self._send_json({"type": "error", "message": display_message})
        if "DialogAudioIdleTimeoutError" in message:
            await self._send_json({"type": "status", "status": "idle"})

    async def _delayed_send_session_start(self, upstream, payload: dict[str, Any]) -> None:
        await asyncio.sleep(0.6)
        await self._send_session_start(upstream, payload)

    async def _finish(self) -> None:
        await self._cancel_task("delayed_start_task")
        if self.upstream and self.session_id:
            try:
                await self.upstream.send(make_json_frame(CLIENT_EVENTS["FINISH_SESSION"], {}, self.session_id))
            finally:
                await self._close_upstream()
        await self._send_json({"type": "status", "status": "idle"})
        await self._close_client_ws()

    async def _close_client_ws(self) -> None:
        try:
            await self.client_ws.close()
        except RuntimeError:
            pass

    async def _close_upstream(self) -> None:
        self.closing_upstream = True
        upstream = self.upstream
        self.upstream = None
        self._finalize_conversation()
        self.session_id = ""
        self.upstream_ready = False
        self._close_recorder()
        if upstream:
            try:
                await upstream.close()
            except Exception:
                pass

    async def _cancel_tasks(self) -> None:
        for attr in ("delayed_start_task", "upstream_task"):
            await self._cancel_task(attr)

    async def _cancel_task(self, attr: str) -> None:
        task = getattr(self, attr)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            setattr(self, attr, None)

    def _close_recorder(self) -> None:
        if self.recorder:
            self.recorder.close()
            self.recorder = None

    def _finalize_conversation(self) -> None:
        if not self.conversation_store:
            return
        transcript = self.conversation_store.read_transcript()
        session_id = self.session_id or getattr(self.conversation_store, "session_id", "")
        memory_extraction = None
        if session_id:
            memory_extraction = self.memory_store.extract_compare_and_persist(
                session_id=session_id,
                agent_profile_id=self.agent_profile_id,
                transcript=transcript,
            )
        self.conversation_store.finalize(memory_extraction=memory_extraction)
        self.conversation_store = None

    def _next_assistant_output_id(self) -> str:
        self.assistant_output_seq += 1
        self.current_assistant_output_id = f"assistant-output-{self.assistant_output_seq}"
        return self.current_assistant_output_id

    def _next_user_output_id(self) -> str:
        self.user_output_seq += 1
        self.current_user_output_id = f"user-output-{self.user_output_seq}"
        return self.current_user_output_id

    def _reset_assistant_turn(self) -> None:
        self.current_assistant_output_id = ""
        self.current_assistant_text = ""
        self.chat_response_output_id = ""
        self.chat_response_text = ""

    async def _handle_user_asr_text(self, text: str) -> None:
        clean_text = _clean_display_text(text)
        if not clean_text:
            return

        output_id = self.current_user_output_id or self._next_user_output_id()
        self.current_user_text = _merge_asr_text(self.current_user_text, clean_text)
        await self._send_json({"type": "event", "event": _make_event("user", self.current_user_text, output_id)})
        await self._send_json(
            _make_voice_turn_text_event(
                session_id=self.session_id,
                turn_id=output_id,
                role="user",
                text=self.current_user_text,
                output_id=output_id,
            )
        )
        await self._send_json(
            _make_transcript_event(
                session_id=self.session_id,
                turn_id=output_id,
                role="user",
                text=self.current_user_text,
                output_id=output_id,
            )
        )
        await self._send_json(
            self.semantic_router.route_text(
                session_id=self.session_id,
                turn_id=output_id,
                text=self.current_user_text,
                source="doubao_s2s",
                agent_profile_id=self.agent_profile_id,
            )
        )

    def _set_agent_profile_from_message(self, message: dict[str, Any]) -> None:
        agent_profile_id = str(message.get("agent_profile_id") or "default").strip()
        self.agent_profile_id = agent_profile_id or "default"

    async def _handle_chat_response_content(self, content: str) -> None:
        text = _clean_display_text(content)
        if not text:
            return

        if not self.chat_response_output_id:
            self.chat_response_output_id = self.current_assistant_output_id or self._next_assistant_output_id()
            self.chat_response_text = text
        else:
            self.chat_response_text = _merge_stream_text(self.chat_response_text, text)

        await self._send_assistant_text(self.chat_response_text, self.chat_response_output_id)

    async def _handle_tts_sentence_text(self, text: str) -> None:
        clean_text = _clean_display_text(text)
        if not clean_text:
            return

        output_id = self.chat_response_output_id or self.current_assistant_output_id or self._next_assistant_output_id()
        if _is_text_already_covered(self.current_assistant_text, clean_text):
            return
        await self._send_assistant_text(clean_text, output_id)

    async def _send_assistant_text(self, text: str, output_id: str) -> None:
        self.current_assistant_output_id = output_id
        self.current_assistant_text = text
        await self._send_json({"type": "event", "event": _make_event("assistant", text, output_id)})
        await self._send_json(
            _make_voice_turn_text_event(
                session_id=self.session_id,
                turn_id=output_id,
                role="assistant",
                text=text,
                output_id=output_id,
            )
        )
        await self._send_json(
            _make_transcript_event(
                session_id=self.session_id,
                turn_id=output_id,
                role="assistant",
                text=text,
                output_id=output_id,
            )
        )

    async def _send_json(self, payload: dict[str, Any]) -> None:
        try:
            await self.client_ws.send_text(json.dumps(payload, ensure_ascii=False))
            self._record_client_debug(payload)
        except Exception:
            pass

    def _record_client_debug(self, payload: dict[str, Any]) -> None:
        payload_type = payload.get("type")
        if payload_type == "voice_turn_text":
            self._record_debug(
                "voice_turn_text",
                {
                    "role": payload.get("role"),
                    "text": payload.get("text"),
                    "turn_id": payload.get("turn_id"),
                },
            )
            return
        if payload_type == "transcript_event":
            if self.conversation_store:
                self.conversation_store.record_transcript(payload)
            self._record_debug(
                "transcript_event",
                {
                    "role": payload.get("role"),
                    "text": payload.get("text"),
                    "turn_id": payload.get("turn_id"),
                },
            )
            return
        if payload_type == "route_decision":
            if self.conversation_store:
                self.conversation_store.record_route_decision(payload)
            self._record_debug(
                "route_decision",
                {
                    "mode": payload.get("mode"),
                    "intent": payload.get("intent"),
                    "scenario_id": payload.get("scenario_id"),
                    "scenario_intent": payload.get("scenario_intent"),
                    "turn_id": payload.get("turn_id"),
                },
            )
            return
        if payload_type == "status":
            self._record_debug("status", {"status": payload.get("status"), "warnings": payload.get("warnings")})
            return
        if payload_type == "error":
            self._record_debug("error", {"message": payload.get("message")})
            return

    def _record_debug(self, kind: str, payload: dict[str, Any]) -> None:
        if self.debug_logger:
            self.debug_logger.record(kind, payload)


def _extract_asr_text(payload: dict[str, Any]) -> str:
    results = payload.get("results")
    if not isinstance(results, list):
        return ""
    texts = [str(item.get("text") or "") for item in results if isinstance(item, dict) and item.get("text")]
    return texts[-1] if texts else ""


def _inject_memory_context(raw_config: dict[str, Any], memory_context: dict[str, Any]) -> dict[str, Any]:
    config = dict(raw_config)
    memory_text = str(memory_context.get("system_role_text") or "").strip()
    if not memory_text:
        return config

    system_role = str(config.get("systemRole") or "").strip()
    config["systemRole"] = f"{system_role}\n\n{memory_text}" if system_role else memory_text
    return config


def _extract_memory_session_ids(message: dict[str, Any]) -> list[str]:
    raw_ids = message.get("memory_session_ids") or message.get("previous_session_ids") or []
    if not isinstance(raw_ids, list):
        return []
    session_ids: list[str] = []
    for raw_id in raw_ids:
        session_id = str(raw_id or "").strip()
        if session_id:
            session_ids.append(session_id)
    return session_ids


def _make_event(event_type: str, text: str, output_id: str | None = None) -> dict[str, str]:
    event = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "text": text,
        "at": datetime.now().strftime("%H:%M:%S"),
    }
    if output_id:
        event["outputId"] = output_id
    return event


def _make_voice_turn_text_event(session_id: str, turn_id: str, role: str, text: str, output_id: str) -> dict[str, str]:
    return {
        "type": "voice_turn_text",
        "session_id": session_id,
        "turn_id": turn_id,
        "role": role,
        "text": text,
        "source": "doubao_s2s",
        "output_id": output_id,
        "at": datetime.now().strftime("%H:%M:%S"),
    }


def _make_transcript_event(session_id: str, turn_id: str, role: str, text: str, output_id: str) -> dict[str, str]:
    return {
        "type": "transcript_event",
        "session_id": session_id,
        "turn_id": turn_id,
        "role": role,
        "text": text,
        "source": "doubao_s2s",
        "output_id": output_id,
        "at": datetime.now().strftime("%H:%M:%S"),
    }


def _make_upstream_debug_payload(frame: ServerFrame) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": frame.event,
        "code": frame.code,
        "message_type": frame.message_type,
        "session_id": frame.session_id,
    }
    if isinstance(frame.payload, bytes):
        payload["payload_bytes"] = len(frame.payload)
    else:
        payload["payload"] = frame.payload
    return payload


def _make_audio_latency_debug_payload(
    session_id: str,
    session_started_at: float,
    first_audio_at: float,
    payload_bytes: int,
) -> dict[str, Any]:
    latency_ms = int(round((first_audio_at - session_started_at) * 1000)) if session_started_at else 0
    return {
        "session_id": session_id,
        "latency_ms": max(0, latency_ms),
        "payload_bytes": payload_bytes,
    }


def _merge_stream_text(previous: str, next_text: str) -> str:
    previous = _collapse_repeated_text(previous)
    next_text = _collapse_repeated_text(next_text)
    if not previous:
        return next_text
    if not next_text or _is_text_already_covered(previous, next_text):
        return previous
    if next_text.startswith(previous):
        return next_text

    max_overlap = min(len(previous), len(next_text))
    for overlap in range(max_overlap, 0, -1):
        if previous[-overlap:] == next_text[:overlap]:
            return previous + next_text[overlap:]
    return previous + next_text


def _merge_asr_text(previous: str, next_text: str) -> str:
    previous = _collapse_repeated_text(previous)
    next_text = _collapse_repeated_text(next_text)
    if not previous:
        return next_text
    if not next_text:
        return previous

    previous_normalized = _normalize_text(previous)
    next_normalized = _normalize_text(next_text)
    if previous_normalized == next_normalized:
        return next_text
    if previous_normalized and previous_normalized in next_normalized:
        return next_text
    if next_normalized and next_normalized in previous_normalized:
        return previous
    if abs(len(_normalize_text(next_text)) - len(_normalize_text(previous))) <= 2:
        return next_text
    return _merge_stream_text(previous, next_text)


def _is_text_already_covered(existing: str, next_text: str) -> bool:
    existing_normalized = _normalize_text(existing)
    next_normalized = _normalize_text(next_text)
    return bool(next_normalized and next_normalized in existing_normalized)


def _collapse_repeated_text(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    half = len(text) // 2
    if len(text) % 2 == 0 and text[:half] == text[half:]:
        return text[:half]
    return text


def _clean_display_text(text: str) -> str:
    text = _collapse_repeated_text(text)
    if not text:
        return ""

    text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[，。！？、；：])", "", text)
    text = re.sub(r"(?<=[，。！？、；：])\s+(?=[\u3400-\u9fff])", "", text)
    return text


def _normalize_upstream_error_message(message: str) -> str:
    if "DialogAudioIdleTimeoutError" in message:
        return "实时语音会话已空闲超时。请重新开始通话后直接说话，或使用下方文本测试。"
    return message


def _normalize_text(text: str) -> str:
    return "".join(char for char in str(text or "") if not char.isspace() and not unicodedata.category(char).startswith("P"))
