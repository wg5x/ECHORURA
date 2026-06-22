from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from ..config import get_volc_headers, get_volc_ws_url, has_volc_credentials
from ..integrations.volc.events import CLIENT_EVENTS, SERVER_EVENTS
from ..integrations.volc.frames import make_audio_frame, make_json_frame, parse_server_frame
from ..integrations.volc.payload import build_start_session_payload, redact_payload
from ..runtime.config_service import create_runtime_session_config, create_scene_runtime_session_config, require_session_user
from ..runtime.voice_recording_service import start_voice_recording


VOLC_CONNECT_MAX_ATTEMPTS = 2
VOLC_CONNECT_RETRY_DELAY_SECONDS = 0.35


class RealtimeGateway:
    def __init__(self, client_ws: WebSocket) -> None:
        self.client_ws = client_ws
        self.upstream = None
        self.upstream_task: asyncio.Task | None = None
        self.delayed_start_task: asyncio.Task | None = None
        self.finish_close_task: asyncio.Task | None = None
        self.session_id = ""
        self.upstream_ready = False
        self.closing_upstream = False
        self.last_tts_text = ""
        self.assistant_output_seq = 0
        self.current_assistant_output_id = ""
        self.current_assistant_text = ""
        self.chat_response_output_id = ""
        self.chat_response_text = ""
        self.current_user_text = ""
        self.client_audio_frames = 0
        self.client_audio_bytes = 0
        self.force_next_assistant_output = False
        self.voice_recording = None

    async def run(self) -> None:
        await self.client_ws.accept()
        try:
            while True:
                message = await self.client_ws.receive()
                if message.get("type") == "websocket.disconnect":
                    _log_realtime_payload("client_disconnect", _make_client_disconnect_log(self))
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

    async def _handle_binary(self, raw: bytes) -> None:
        self.client_audio_frames += 1
        self.client_audio_bytes += len(raw)
        if self.client_audio_frames <= 3 or self.client_audio_frames % 50 == 0:
            _log_realtime_payload(
                "client_audio",
                _make_client_audio_log(self.client_audio_frames, len(raw), self.client_audio_bytes),
            )
        self._record_client_audio(raw)
        if self.upstream and self.session_id:
            try:
                await self.upstream.send(make_audio_frame(CLIENT_EVENTS["TASK_REQUEST"], raw, self.session_id))
            except Exception:
                await self._send_json({"type": "error", "message": "发送音频到火山实时语音失败。"})

    async def _handle_text(self, raw: str) -> None:
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_json({"type": "error", "message": "无法解析客户端消息。"})
            return

        _log_realtime_payload("client_message", _make_client_message_log(message))

        if message.get("type") == "start":
            await self._cancel_tasks()
            await self._close_upstream()
            self._close_voice_recording()
            self.client_audio_frames = 0
            self.client_audio_bytes = 0

            try:
                payload = message.get("payload") or {}
                user_id = payload.get("userId") or _nested_get(payload, "user", "id")
                scene_id = payload.get("sceneId") or _nested_get(payload, "scene", "id")
                if user_id:
                    require_session_user(payload.get("sessionToken"), user_id)
                    runtime = await create_runtime_session_config(
                        user_id,
                        scene_id,
                        memory_enabled=payload.get("memoryEnabled", True),
                    )
                else:
                    runtime = await create_scene_runtime_session_config(
                        scene_id,
                        memory_enabled=payload.get("memoryEnabled", True),
                    )
                session = build_start_session_payload(runtime["config"])
                recording_metadata = {
                    "requestId": payload.get("requestId"),
                    "userId": _nested_get(runtime, "user", "id") or "scene_route",
                    "sceneId": _nested_get(runtime, "scene", "id"),
                    "recordAudio": payload.get("recordAudio"),
                }
            except PermissionError as exc:
                await self._send_json({"type": "error", "message": str(exc) or "当前用户没有被分配这个场景。"})
                await self._send_json({"type": "status", "status": "idle", "mode": "volcengine"})
                return
            except Exception as exc:
                await self._send_json({"type": "error", "message": str(exc) or "配置无效。"})
                return

            if not has_volc_credentials():
                await self._send_json(
                    {
                        "type": "error",
                        "message": "缺少火山实时语音真实链路配置：请在 apps/api/.local/env/.env.local 中配置 VOLC_API_APP_ID 和 VOLC_API_ACCESS_KEY。",
                        "payload": redact_payload(session["payload"]),
                        "warnings": session["warnings"],
                    }
                )
                await self._send_json(
                    {"type": "status", "status": "idle", "mode": "volcengine", "warnings": session["warnings"]}
                )
                return

            await self._start_volc_session(session, recording_metadata)
            return

        if message.get("type") == "user_text":
            text = str(message.get("text") or "").strip()
            if not text:
                return
            self._prepare_for_user_input()
            if self.upstream and self.session_id:
                try:
                    await self.upstream.send(make_json_frame(CLIENT_EVENTS["CHAT_TEXT_QUERY"], {"content": text}, self.session_id))
                except Exception:
                    await self._send_json({"type": "error", "message": "发送文本到火山实时语音失败。"})
                return

            await self._send_json({"type": "error", "message": "真实链路尚未连接成功，不能发送文本对话。"})
            return

        if message.get("type") == "finish":
            await self._finish()
            return

        if message.get("type") == "interrupt":
            target_output_id = str(message.get("targetOutputId") or self.current_assistant_output_id or "")
            self._reset_chat_response_buffer()
            self.force_next_assistant_output = True
            if self.upstream and self.session_id:
                try:
                    self.last_tts_text = ""
                    await self.upstream.send(make_json_frame(CLIENT_EVENTS["CLIENT_INTERRUPT"], {}, self.session_id))
                except Exception:
                    await self._send_json({"type": "error", "message": "发送打断事件到火山实时语音失败。"})
                    return
            await self._send_json({"type": "interrupt_ack", "targetOutputId": target_output_id})
            return

    async def _start_volc_session(self, session: dict[str, Any], recording_metadata: dict[str, Any] | None = None) -> None:
        payload = session["payload"]
        warnings = session["warnings"]
        config = session["config"]
        connect_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.upstream_ready = False
        self.closing_upstream = False
        self.last_tts_text = ""
        self.assistant_output_seq = 0
        self.current_assistant_output_id = ""
        self.current_assistant_text = ""
        self.current_user_text = ""
        self._reset_chat_response_buffer()
        self.force_next_assistant_output = False
        recording_enabled = bool((recording_metadata or {}).get("recordAudio"))
        self.voice_recording = start_voice_recording(self.session_id, recording_metadata, enabled=recording_enabled)

        await self._send_json(
            {
                "type": "payload",
                "payload": redact_payload(payload),
                "warnings": warnings,
                "mode": "volcengine",
            }
        )
        await self._send_json(
            {
                "type": "status",
                "status": "connecting",
                "mode": "volcengine",
                "warnings": warnings,
                "sessionId": self.session_id,
                "requestId": (recording_metadata or {}).get("requestId"),
            }
        )

        try:
            self.upstream = await _connect_volc_upstream(connect_id)
            await self.upstream.send(make_json_frame(CLIENT_EVENTS["START_CONNECTION"], {}))
            self.delayed_start_task = asyncio.create_task(self._delayed_send_session_start(self.upstream, payload))
            self.upstream_task = asyncio.create_task(self._upstream_loop(self.upstream, payload, warnings, config))
        except Exception as exc:
            self._close_voice_recording()
            await self._send_json(
                {
                    "type": "error",
                    "message": f"连接火山实时语音 WebSocket 失败：{exc}",
                    "payload": redact_payload(payload),
                    "warnings": warnings,
                }
            )
            await self._send_json({"type": "status", "status": "idle", "mode": "volcengine", "warnings": warnings})

    async def _upstream_loop(self, upstream, payload: dict[str, Any], warnings: list[str], config: dict[str, Any]) -> None:
        session_started = False
        session_finished = False
        try:
            async for data in upstream:
                if self.upstream is not upstream:
                    return
                frame = parse_server_frame(data)
                if not frame:
                    continue

                _log_realtime_payload("server_frame", _make_server_frame_log(frame))

                if frame.message_type == 0x0F:
                    error_text = (
                        frame.payload.get("error")
                        if isinstance(frame.payload, dict) and frame.payload.get("error")
                        else f"火山 API 返回错误{'：' + str(frame.code) if frame.code else ''}"
                    )
                    await self._send_json(
                        {"type": "error", "message": error_text, "payload": redact_payload(payload), "warnings": warnings}
                    )
                    continue

                if frame.event == SERVER_EVENTS["CONNECTION_STARTED"]:
                    await self._send_session_start(upstream, payload)
                    continue

                if frame.event in (SERVER_EVENTS["CONNECTION_FAILED"], SERVER_EVENTS["SESSION_FAILED"]):
                    error_text = frame.payload.get("error") if isinstance(frame.payload, dict) else None
                    await self._send_json(
                        {
                            "type": "error",
                            "message": error_text or "火山实时语音连接失败。",
                            "payload": redact_payload(payload),
                            "warnings": warnings,
                        }
                    )
                    continue

                if frame.event == SERVER_EVENTS["SESSION_STARTED"]:
                    session_started = True
                    await self._send_json({"type": "status", "status": "connected", "mode": "volcengine", "warnings": warnings})
                    if config.get("openingLine"):
                        await self._handle_assistant_text(config["openingLine"])
                        await upstream.send(
                            make_json_frame(CLIENT_EVENTS["SAY_HELLO"], {"content": config["openingLine"]}, self.session_id)
                        )
                    continue

                if frame.event == SERVER_EVENTS["USAGE_RESPONSE"] and isinstance(frame.payload, dict) and frame.payload.get("usage"):
                    usage = frame.payload["usage"]
                    total = sum(float(value) if _is_number_like(value) else 0 for value in usage.values())
                    await self._send_json({"type": "usage", "tokens": int(total)})
                    continue

                if frame.event == SERVER_EVENTS["ASR_RESPONSE"] and isinstance(frame.payload, dict) and frame.payload.get("results"):
                    raw_texts = [str(item.get("text") or "") for item in frame.payload["results"] if isinstance(item, dict)]
                    text = _merge_result_texts(raw_texts)
                    emitted_text = _merge_asr_text(self.current_user_text, text)
                    _log_realtime_payload(
                        "asr_response",
                        _make_asr_payload_log(frame.payload, raw_texts, emitted_text),
                    )
                    if emitted_text:
                        await self._emit_asr_text(emitted_text)
                    continue

                if frame.event == SERVER_EVENTS["CHAT_RESPONSE"] and isinstance(frame.payload, dict) and frame.payload.get("content"):
                    await self._handle_chat_response_content(frame.payload["content"])
                    continue

                if frame.event == SERVER_EVENTS["TTS_SENTENCE_START"] and isinstance(frame.payload, dict) and frame.payload.get("text"):
                    await self._handle_tts_sentence_start_text(frame.payload["text"])
                    continue

                if frame.event == SERVER_EVENTS["TTS_SENTENCE_END"] and isinstance(frame.payload, dict) and frame.payload.get("text"):
                    await self._handle_tts_sentence_end_text(frame.payload["text"])
                    continue

                if frame.event == SERVER_EVENTS["TTS_RESPONSE"] and isinstance(frame.payload, bytes):
                    await self._handle_tts_audio(frame.payload)
                    continue

                if frame.event in (SERVER_EVENTS["TTS_ENDED"], SERVER_EVENTS["CHAT_ENDED"]):
                    self._reset_chat_response_buffer()
                    continue

                if frame.event in (SERVER_EVENTS["SESSION_FINISHED"], SERVER_EVENTS["CONNECTION_FINISHED"]):
                    session_finished = True
                    self.session_id = ""
                    self.upstream_ready = False
                    await self._send_json({"type": "status", "status": "idle", "mode": "volcengine", "warnings": warnings})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if self.closing_upstream:
                return
            message = (
                f"火山实时语音连接已关闭：{exc}"
                if not session_started
                else f"火山实时语音连接已中断：{exc}"
            )
            await self._send_json({"type": "error", "message": message, "payload": redact_payload(payload), "warnings": warnings})
            await self._send_json({"type": "status", "status": "idle", "mode": "volcengine", "warnings": warnings})
        finally:
            if self.upstream is upstream:
                self.upstream = None
                self._close_voice_recording()
            self.session_id = ""
            self.upstream_ready = False
            if self.closing_upstream or session_finished:
                self.closing_upstream = False

    async def _send_session_start(self, upstream, payload: dict[str, Any]) -> None:
        if self.upstream is not upstream or self.upstream_ready or not self.session_id:
            return
        self.upstream_ready = True
        await upstream.send(make_json_frame(CLIENT_EVENTS["START_SESSION"], payload, self.session_id))

    async def _delayed_send_session_start(self, upstream, payload: dict[str, Any]) -> None:
        await asyncio.sleep(0.6)
        await self._send_session_start(upstream, payload)

    async def _finish(self) -> None:
        await self._cancel_task("delayed_start_task")
        if self.upstream and self.session_id:
            try:
                await self.upstream.send(make_json_frame(CLIENT_EVENTS["FINISH_SESSION"], {}, self.session_id))
            finally:
                self.finish_close_task = asyncio.create_task(self._close_client_after_finish())
            return

        await self._send_json(
            {
                "type": "event",
                "event": _make_event("system", "SessionFinished: 会话已结束，WebSocket 可复用。"),
            }
        )
        await self._send_json({"type": "status", "status": "idle"})
        await self._close_client_ws()

    async def _close_client_after_finish(self) -> None:
        await asyncio.sleep(0.5)
        self.closing_upstream = True
        if self.upstream:
            await self.upstream.close()
        self._close_voice_recording()
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
        self.session_id = ""
        self.upstream_ready = False
        self._close_voice_recording()
        if upstream:
            try:
                await upstream.close()
            except Exception:
                pass

    async def _cancel_tasks(self) -> None:
        for attr in ("delayed_start_task", "finish_close_task", "upstream_task"):
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

    def _next_assistant_output_id(self) -> str:
        self.assistant_output_seq += 1
        self.current_assistant_output_id = f"assistant-output-{self.assistant_output_seq}"
        return self.current_assistant_output_id

    def _assistant_output_id_for_text(self, text: str) -> str:
        if not self.current_assistant_output_id or not _is_repeated_text(self.current_assistant_text, text):
            self._next_assistant_output_id()
        self.current_assistant_text = text
        return self.current_assistant_output_id

    def _reset_chat_response_buffer(self) -> None:
        self.chat_response_output_id = ""
        self.chat_response_text = ""

    def _reset_user_asr_buffer(self) -> None:
        self.current_user_text = ""

    def _prepare_for_user_input(self) -> None:
        self.force_next_assistant_output = True
        self._reset_chat_response_buffer()

    def _assistant_output_id_for_new_turn(self, text: str) -> str:
        if self.force_next_assistant_output:
            self.force_next_assistant_output = False
            return self._next_assistant_output_id()
        return self._assistant_output_id_for_text(text)

    async def _handle_chat_response_content(self, raw_content: Any) -> None:
        content = _collapse_repeated_text(str(raw_content))
        if not content:
            return

        if not self.chat_response_output_id:
            output_id = self._assistant_output_id_for_new_turn(content)
            self.chat_response_output_id = output_id
            self.chat_response_text = content
            await self._emit_assistant_text(content, "CHAT_RESPONSE", output_id)
            return

        merged_text = _merge_stream_text(self.chat_response_text, content)
        self.chat_response_text = merged_text
        await self._emit_assistant_text(merged_text, "CHAT_RESPONSE", self.chat_response_output_id)

    async def _handle_tts_sentence_start_text(self, raw_text: Any) -> None:
        self.last_tts_text = _collapse_repeated_text(str(raw_text))
        if self.chat_response_output_id:
            if (
                self.current_assistant_output_id == self.chat_response_output_id
                and _is_text_already_covered(self.current_assistant_text, self.last_tts_text)
            ):
                return
            await self._emit_assistant_text(self.last_tts_text, "TTS_SENTENCE_START", self.chat_response_output_id)
            return
        await self._handle_assistant_text(self.last_tts_text, "TTS_SENTENCE_START")

    async def _handle_tts_sentence_end_text(self, raw_text: Any) -> None:
        text = _collapse_repeated_text(str(raw_text))
        output_id = self.current_assistant_output_id or None
        _log_realtime_payload("tts_sentence_end", _make_text_payload_log("TTS_SENTENCE_END", text, output_id))
        if self.chat_response_output_id:
            if (
                self.current_assistant_output_id == self.chat_response_output_id
                and _is_text_already_covered(self.current_assistant_text, text)
            ):
                return
            await self._emit_assistant_text(text, "TTS_SENTENCE_END", self.chat_response_output_id)
            return

        if _is_text_already_covered(self.current_assistant_text, text):
            return
        await self._handle_assistant_text(text, "TTS_SENTENCE_END")

    async def _handle_assistant_text(self, text: str, source_event: str = "TTS_SENTENCE_START") -> None:
        output_id = self._assistant_output_id_for_text(text)
        await self._emit_assistant_text(text, source_event, output_id)

    async def _emit_asr_text(self, text: str) -> None:
        self.current_user_text = _merge_asr_text(self.current_user_text, text)
        self._prepare_for_user_input()
        await self._send_json({"type": "event", "event": _make_event("asr", f"ASRResponse: {self.current_user_text}")})

    async def _emit_assistant_text(self, text: str, source_event: str, output_id: str) -> None:
        self._reset_user_asr_buffer()
        self.current_assistant_output_id = output_id
        self.current_assistant_text = text
        _log_realtime_payload(
            "assistant_text",
            _make_text_payload_log(source_event, text, output_id),
        )
        await self._send_json(
            {
                "type": "event",
                "event": _make_event("assistant", f"ChatResponse: {text}", output_id),
            }
        )

    async def _handle_tts_audio(self, audio: bytes) -> None:
        output_id = self.current_assistant_output_id or self._next_assistant_output_id()
        _log_realtime_payload("tts_response", _make_audio_payload_log(output_id, len(audio)))
        self._record_assistant_audio(audio)
        await self._send_json(
            {
                "type": "audio",
                "mime": "audio/pcm; format=s16le; rate=24000",
                "data": _to_base64(audio),
                "outputId": output_id,
            }
        )

    async def _send_json(self, payload: dict[str, Any]) -> None:
        try:
            await self.client_ws.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass

    def _record_client_audio(self, audio: bytes) -> None:
        if not self.voice_recording:
            return
        try:
            self.voice_recording.write_client_audio(audio)
        except Exception:
            self._close_voice_recording()

    def _record_assistant_audio(self, audio: bytes) -> None:
        if not self.voice_recording:
            return
        try:
            self.voice_recording.write_assistant_audio(audio)
        except Exception:
            self._close_voice_recording()

    def _close_voice_recording(self) -> None:
        recording = self.voice_recording
        self.voice_recording = None
        if not recording:
            return
        try:
            recording.close()
        except Exception:
            pass


async def _connect_volc_upstream(connect_id: str):
    last_error: Exception | None = None
    for attempt in range(1, VOLC_CONNECT_MAX_ATTEMPTS + 1):
        try:
            return await websockets.connect(get_volc_ws_url(), additional_headers=get_volc_headers(connect_id))
        except Exception as exc:
            last_error = exc
            _log_realtime_payload("upstream_connect_error", _make_upstream_connect_error_log(exc, attempt))
            if attempt >= VOLC_CONNECT_MAX_ATTEMPTS or not _is_retryable_upstream_connect_error(exc):
                raise
            await asyncio.sleep(VOLC_CONNECT_RETRY_DELAY_SECONDS)

    raise last_error or RuntimeError("连接火山实时语音 WebSocket 失败。")


def _is_retryable_upstream_connect_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None) or getattr(error, "status", None)
    if status_code == 403:
        return True
    return "403" in str(error)


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


def _log_realtime_payload(kind: str, payload: dict[str, Any]) -> None:
    if not _is_realtime_payload_log_enabled():
        return
    print(
        "[REALTIME-PAYLOAD] "
        + json.dumps(
            {
                "kind": kind,
                "payload": payload,
            },
            ensure_ascii=False,
            default=str,
        ),
        flush=True,
    )


def _is_realtime_payload_log_enabled() -> bool:
    return str(os.environ.get("AI_ENGINE_REALTIME_PAYLOAD_LOG") or "").strip().lower() in {"1", "true", "yes", "on"}


def _make_asr_payload_log(raw_payload: dict[str, Any], raw_texts: list[str], merged_text: str) -> dict[str, Any]:
    return {
        "event": "ASR_RESPONSE",
        "rawResults": raw_payload.get("results"),
        "rawTexts": [_make_text_debug_item(text) for text in raw_texts],
        "mergedText": _make_text_debug_item(merged_text),
    }


def _make_text_debug_item(text: str) -> dict[str, Any]:
    return {
        "text": text,
        "normalized": _normalize_text_for_repeat_check(text),
        "codepoints": [f"U+{ord(char):04X}" for char in text],
    }


def _make_text_payload_log(event: str, text: str, output_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": event,
        "text": _make_text_debug_item(text),
    }
    if output_id:
        payload["outputId"] = output_id
    return payload


def _make_audio_payload_log(output_id: str, byte_length: int) -> dict[str, Any]:
    return {
        "event": "TTS_RESPONSE",
        "outputId": output_id,
        "byteLength": byte_length,
    }


def _make_upstream_connect_error_log(error: Exception, attempt: int) -> dict[str, Any]:
    return {
        "attempt": attempt,
        "maxAttempts": VOLC_CONNECT_MAX_ATTEMPTS,
        "errorType": type(error).__name__,
        "statusCode": getattr(error, "status_code", None) or getattr(error, "status", None),
        "retryable": _is_retryable_upstream_connect_error(error),
    }


def _make_client_message_log(message: dict[str, Any]) -> dict[str, Any]:
    message_type = str(message.get("type") or "")
    payload: dict[str, Any] = {"type": message_type}
    if message_type == "start":
        raw_payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        payload["payload"] = {
            "userId": raw_payload.get("userId"),
            "sceneId": raw_payload.get("sceneId"),
            "memoryEnabled": raw_payload.get("memoryEnabled"),
            "hasSessionToken": bool(raw_payload.get("sessionToken")),
        }
    elif message_type == "interrupt":
        payload["targetOutputId"] = message.get("targetOutputId")
    elif message_type == "user_text":
        payload["text"] = _make_text_debug_item(str(message.get("text") or ""))
    return payload


def _make_client_audio_log(frame_count: int, byte_length: int, total_bytes: int) -> dict[str, Any]:
    return {
        "frames": frame_count,
        "byteLength": byte_length,
        "totalBytes": total_bytes,
    }


def _make_client_disconnect_log(gateway: RealtimeGateway) -> dict[str, Any]:
    return {
        "audioFrames": gateway.client_audio_frames,
        "audioBytes": gateway.client_audio_bytes,
        "sessionId": gateway.session_id,
        "upstreamReady": gateway.upstream_ready,
    }


def _make_server_frame_log(frame: Any) -> dict[str, Any]:
    payload = frame.payload
    if isinstance(payload, bytes):
        payload_summary: Any = {"byteLength": len(payload)}
    elif isinstance(payload, dict):
        payload_summary = {key: payload.get(key) for key in ("error", "text", "content", "usage") if key in payload}
        if "results" in payload:
            payload_summary["resultsCount"] = len(payload["results"]) if isinstance(payload["results"], list) else None
    else:
        payload_summary = payload
    return {
        "event": frame.event,
        "messageType": frame.message_type,
        "code": frame.code,
        "sessionId": frame.session_id,
        "payload": payload_summary,
    }


def _nested_get(value: dict[str, Any], key: str, child_key: str) -> Any:
    child = value.get(key)
    return child.get(child_key) if isinstance(child, dict) else None


def _is_number_like(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _is_repeated_text(previous: str, current: str) -> bool:
    previous_text = previous.strip()
    current_text = current.strip()
    if not previous_text or not current_text:
        return False
    normalized_previous = _normalize_text_for_repeat_check(previous_text)
    normalized_current = _normalize_text_for_repeat_check(current_text)
    dedup_previous = _normalize_assistant_dedup_text(normalized_previous)
    dedup_current = _normalize_assistant_dedup_text(normalized_current)
    return (
        previous_text == current_text
        or previous_text in current_text
        or current_text in previous_text
        or (
            bool(normalized_previous)
            and bool(normalized_current)
            and (normalized_previous in normalized_current or normalized_current in normalized_previous)
        )
        or (
            bool(dedup_previous)
            and bool(dedup_current)
            and (dedup_previous in dedup_current or dedup_current in dedup_previous)
        )
        or _is_highly_similar_text(dedup_previous, dedup_current)
    )


def _merge_result_texts(parts: Any) -> str:
    candidates = [str(part or "").strip() for part in parts if str(part or "").strip()]
    if not candidates:
        return ""

    selected = candidates[0]
    for text in candidates[1:]:
        selected = _merge_asr_text(selected, text)
    return _collapse_repeated_text(selected)


def _merge_asr_text(previous: str, current: str) -> str:
    previous_text = previous.strip()
    current_text = current.strip()
    if not previous_text:
        return current_text
    if not current_text:
        return previous_text

    normalized_previous = _normalize_text_for_repeat_check(previous_text)
    normalized_current = _normalize_text_for_repeat_check(current_text)
    if normalized_previous and normalized_current:
        if normalized_previous == normalized_current:
            return _prefer_asr_candidate(previous_text, current_text)
        if normalized_previous in normalized_current:
            return current_text
        if normalized_current in normalized_previous:
            return _prefer_asr_candidate(previous_text, current_text)

    if _is_repeated_text(previous_text, current_text):
        return _prefer_asr_candidate(previous_text, current_text)

    if current_text.startswith(previous_text) or previous_text in current_text:
        return current_text
    if previous_text.endswith(current_text) or current_text in previous_text:
        return previous_text

    return _append_with_overlap(previous_text, current_text)


def _merge_stream_text(previous: str, current: str) -> str:
    previous_text = previous.strip()
    current_text = current.strip()
    if not previous_text:
        return current_text
    if not current_text:
        return previous_text

    if not _normalize_text_for_repeat_check(current_text):
        return _collapse_repeated_text(_append_with_overlap(previous_text, current_text))
    if current_text.startswith(previous_text) or previous_text in current_text:
        return _collapse_repeated_text(current_text)
    if current_text in previous_text:
        return _collapse_repeated_text(previous_text)
    return _collapse_repeated_text(_append_with_overlap(previous_text, current_text))


def _is_text_already_covered(previous: str, current: str) -> bool:
    previous_text = previous.strip()
    current_text = current.strip()
    if not previous_text or not current_text:
        return False
    normalized_previous = _normalize_text_for_repeat_check(previous_text)
    normalized_current = _normalize_text_for_repeat_check(current_text)
    return (
        previous_text == current_text
        or current_text in previous_text
        or (
            bool(normalized_previous)
            and bool(normalized_current)
            and normalized_current in normalized_previous
        )
    )


def _prefer_asr_candidate(previous: str, current: str) -> str:
    normalized_previous = _normalize_text_for_repeat_check(previous)
    normalized_current = _normalize_text_for_repeat_check(current)
    previous_punctuation = _punctuation_count(previous)
    current_punctuation = _punctuation_count(current)

    if normalized_previous == normalized_current:
        if _ascii_digit_count(current) > _ascii_digit_count(previous):
            return current
        if _ascii_digit_count(previous) > _ascii_digit_count(current):
            return previous

    if normalized_current in normalized_previous:
        coverage = len(normalized_current) / max(1, len(normalized_previous))
        if coverage >= 0.72 and current_punctuation > previous_punctuation:
            return current
        return previous

    if normalized_previous in normalized_current:
        return current

    if len(normalized_current) > len(normalized_previous):
        return current
    if len(normalized_previous) > len(normalized_current):
        return previous
    if current_punctuation > previous_punctuation:
        return current
    return current


def _append_with_overlap(previous: str, current: str) -> str:
    max_overlap = min(len(previous), len(current))
    for length in range(max_overlap, 0, -1):
        if previous.endswith(current[:length]):
            return previous + current[length:]
    return previous + current


def _collapse_repeated_text(text: str) -> str:
    current = _collapse_visual_repeated_text(_normalize_invisible_spaces(text.strip()))
    current = _collapse_adjacent_repeated_chunks(current)
    changed = True
    while changed:
        changed = False
        for length in range(len(current) // 2, 0, -1):
            repeated = current[:length]
            rest = current[length:]
            if repeated and rest.startswith(repeated):
                current = _collapse_adjacent_repeated_chunks(repeated + rest[length:])
                changed = True
                break
    return current


def _collapse_visual_repeated_text(text: str) -> str:
    compact = _normalize_text_for_repeat_check(text)
    if not compact or len(compact) % 2 != 0:
        return text

    half_length = len(compact) // 2
    if compact[:half_length] != compact[half_length:]:
        return text

    seen = 0
    for index, char in enumerate(text):
        if char.isalnum():
            seen += 1
            if seen == half_length:
                return text[: index + 1].strip()
    return text


def _collapse_adjacent_repeated_chunks(text: str) -> str:
    import re

    current = text.strip()
    changed = True
    while changed:
        next_text = re.sub(r"([\w\u4e00-\u9fff]{2,})([，,。！？!?、；;\s]*)\1", r"\1", current)
        next_text = re.sub(
            r"([\w\u4e00-\u9fff]{2,})([，,。！？!?、；;\s]*(?:噢|哦|啊|呀|呃|嗯|额|哈)[，,。！？!?、；;\s]*)\1",
            r"\1",
            next_text,
        ).strip()
        changed = next_text != current
        current = next_text
    return current


def _normalize_text_for_repeat_check(text: str) -> str:
    compact = "".join(char for char in _normalize_invisible_spaces(text).strip() if char.isalnum())
    return _normalize_spoken_digits(_normalize_spoken_decades(compact))


def _normalize_assistant_dedup_text(text: str) -> str:
    return text.rstrip("啊呀呢吧哦噢喔啦哈").replace("感谢您的理解", "谢谢您的理解").replace("的状态", "状态")


def _is_highly_similar_text(previous: str, current: str) -> bool:
    min_length = min(len(previous), len(current))
    if min_length < 8:
        return False
    ratio = SequenceMatcher(None, previous, current, autojunk=False).ratio()
    if min_length >= 24:
        return ratio >= 0.92
    return ratio >= 0.94 and _shared_edge_coverage(previous, current) >= 0.9


def _shared_edge_coverage(previous: str, current: str) -> float:
    if not previous or not current:
        return 0
    prefix = 0
    limit = min(len(previous), len(current))
    while prefix < limit and previous[prefix] == current[prefix]:
        prefix += 1
    suffix_limit = limit - prefix
    suffix = 0
    while suffix < suffix_limit and previous[len(previous) - 1 - suffix] == current[len(current) - 1 - suffix]:
        suffix += 1
    return (prefix + suffix) / max(1, limit)


def _normalize_spoken_decades(text: str) -> str:
    return (
        text.replace("八零后", "80后")
        .replace("八0后", "80后")
        .replace("80后", "80后")
        .replace("九零后", "90后")
        .replace("九0后", "90后")
        .replace("零零后", "00后")
        .replace("〇〇后", "00后")
        .replace("零0后", "00后")
    )


def _normalize_spoken_digits(text: str) -> str:
    digit_words = {
        "零": "0",
        "〇": "0",
        "一": "1",
        "二": "2",
        "两": "2",
        "三": "3",
        "四": "4",
        "五": "5",
        "六": "6",
        "七": "7",
        "八": "8",
        "九": "9",
    }
    return "".join(digit_words.get(char, char) for char in text)


def _normalize_invisible_spaces(text: str) -> str:
    return text.replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ")


def _punctuation_count(text: str) -> int:
    return sum(1 for char in text if not char.isalnum() and not char.isspace())


def _ascii_digit_count(text: str) -> int:
    return sum(1 for char in text if "0" <= char <= "9")


def _to_base64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")
