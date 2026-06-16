from __future__ import annotations

import asyncio
import base64
import json
import uuid
from datetime import datetime
from typing import Any

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from ..config import get_volc_headers, get_volc_ws_url, has_volc_credentials
from ..integrations.volc.events import CLIENT_EVENTS, SERVER_EVENTS
from ..integrations.volc.frames import make_audio_frame, make_json_frame, parse_server_frame
from ..integrations.volc.payload import build_start_session_payload, redact_payload


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

    async def _handle_binary(self, raw: bytes) -> None:
        if not self.upstream or not self.session_id:
            return
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

        if message.get("type") == "start":
            await self._cancel_tasks()
            await self._close_upstream()
            if not has_volc_credentials():
                await self._send_json({"type": "error", "message": "缺少 VOLC_API_APP_ID 或 VOLC_API_ACCESS_KEY。"})
                await self._send_json({"type": "status", "status": "idle"})
                return

            try:
                session = build_start_session_payload(message.get("config") or {})
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

        if message.get("type") == "interrupt":
            if self.upstream and self.session_id:
                try:
                    await self.upstream.send(make_json_frame(CLIENT_EVENTS["CLIENT_INTERRUPT"], {}, self.session_id))
                except Exception:
                    await self._send_json({"type": "error", "message": "发送打断事件到火山实时语音失败。"})
                    return
            await self._send_json({"type": "interrupt_ack", "targetOutputId": self.current_assistant_output_id})
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

                if frame.message_type == 0x0F:
                    error_text = frame.payload.get("error") if isinstance(frame.payload, dict) else None
                    await self._send_json({"type": "error", "message": error_text or f"火山 API 返回错误：{frame.code}"})
                    continue

                if frame.event == SERVER_EVENTS["CONNECTION_STARTED"]:
                    await self._send_session_start(upstream, payload)
                    continue

                if frame.event in (SERVER_EVENTS["CONNECTION_FAILED"], SERVER_EVENTS["SESSION_FAILED"]):
                    error_text = frame.payload.get("error") if isinstance(frame.payload, dict) else None
                    await self._send_json({"type": "error", "message": error_text or "火山实时语音连接失败。"})
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
                    self.session_id = ""
                    self.upstream_ready = False
                    await self._send_json({"type": "status", "status": "idle", "warnings": warnings})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if not self.closing_upstream:
                await self._send_json({"type": "error", "message": f"火山实时语音连接已中断：{exc}"})
                await self._send_json({"type": "status", "status": "idle", "warnings": warnings})
        finally:
            if self.upstream is upstream:
                self.upstream = None
            self.session_id = ""
            self.upstream_ready = False

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
        self.session_id = ""
        self.upstream_ready = False
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
        clean_text = _collapse_repeated_text(text)
        if not clean_text:
            return

        output_id = self.current_user_output_id or self._next_user_output_id()
        self.current_user_text = _merge_asr_text(self.current_user_text, clean_text)
        await self._send_json({"type": "event", "event": _make_event("user", self.current_user_text, output_id)})

    async def _handle_chat_response_content(self, content: str) -> None:
        text = _collapse_repeated_text(content)
        if not text:
            return

        if not self.chat_response_output_id:
            self.chat_response_output_id = self.current_assistant_output_id or self._next_assistant_output_id()
            self.chat_response_text = text
        else:
            self.chat_response_text = _merge_stream_text(self.chat_response_text, text)

        await self._send_assistant_text(self.chat_response_text, self.chat_response_output_id)

    async def _handle_tts_sentence_text(self, text: str) -> None:
        clean_text = _collapse_repeated_text(text)
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

    async def _send_json(self, payload: dict[str, Any]) -> None:
        try:
            await self.client_ws.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass


def _extract_asr_text(payload: dict[str, Any]) -> str:
    results = payload.get("results")
    if not isinstance(results, list):
        return ""
    texts = [str(item.get("text") or "") for item in results if isinstance(item, dict) and item.get("text")]
    return texts[-1] if texts else ""


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
    if not next_text or _is_text_already_covered(previous, next_text):
        return previous
    if _is_text_already_covered(next_text, previous):
        return next_text
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


def _normalize_text(text: str) -> str:
    return "".join(str(text or "").split())
