from __future__ import annotations

import asyncio
import uuid
from typing import Any

import websockets

from ..config import get_volc_headers, get_volc_ws_url, has_volc_credentials
from ..integrations.volc.events import CLIENT_EVENTS, SERVER_EVENTS
from ..integrations.volc.frames import make_json_frame, parse_server_frame
from ..integrations.volc.payload import build_start_session_payload
from ..shared.value_utils import to_string_value


async def request_voice_preview(raw_config: dict[str, Any], raw_text: Any) -> dict[str, Any]:
    if not has_volc_credentials():
        raise ValueError("缺少火山实时语音真实链路配置：请在 apps/api/.local/env/.env.local 中配置 VOLC_API_APP_ID 和 VOLC_API_ACCESS_KEY。")

    try:
        return await asyncio.wait_for(_request_voice_preview(raw_config, raw_text), timeout=12)
    except TimeoutError as exc:
        raise ValueError("音色试听超时，请稍后再试。") from exc


async def _request_voice_preview(raw_config: dict[str, Any], raw_text: Any) -> dict[str, Any]:
    preview_text = to_string_value(raw_text, "你好，我是豆包，很高兴和你语音对话。")[:80]
    session = build_start_session_payload({**(raw_config or {}), "openingLine": ""})
    payload = session["payload"]
    warnings = session["warnings"]
    connect_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    chunks: list[bytes] = []
    upstream_ready = False
    session_started = False

    async with websockets.connect(get_volc_ws_url(), additional_headers=get_volc_headers(connect_id)) as upstream:
        async def send_session_start() -> None:
            nonlocal upstream_ready
            if upstream_ready:
                return
            upstream_ready = True
            await upstream.send(make_json_frame(CLIENT_EVENTS["START_SESSION"], payload, session_id))

        await upstream.send(make_json_frame(CLIENT_EVENTS["START_CONNECTION"], {}))
        delayed_start = asyncio.create_task(_delayed(0.6, send_session_start))

        try:
            while True:
                try:
                    data = await asyncio.wait_for(upstream.recv(), timeout=0.7 if chunks else None)
                except TimeoutError:
                    if chunks:
                        return {"audio": b"".join(chunks), "warnings": warnings}
                    raise

                frame = parse_server_frame(data)
                if not frame:
                    continue

                if frame.message_type == 0x0F:
                    error_text = (
                        frame.payload.get("error")
                        if isinstance(frame.payload, dict) and frame.payload.get("error")
                        else f"火山 API 返回错误{'：' + str(frame.code) if frame.code else ''}"
                    )
                    raise ValueError(error_text)

                if frame.event == SERVER_EVENTS["CONNECTION_STARTED"]:
                    await send_session_start()
                    continue

                if frame.event in (SERVER_EVENTS["CONNECTION_FAILED"], SERVER_EVENTS["SESSION_FAILED"]):
                    error_text = frame.payload.get("error") if isinstance(frame.payload, dict) else None
                    raise ValueError(error_text or "火山实时语音连接失败。")

                if frame.event == SERVER_EVENTS["SESSION_STARTED"]:
                    session_started = True
                    await upstream.send(make_json_frame(CLIENT_EVENTS["SAY_HELLO"], {"content": preview_text}, session_id))
                    continue

                if frame.event == SERVER_EVENTS["TTS_RESPONSE"] and isinstance(frame.payload, bytes):
                    chunks.append(frame.payload)
                    continue

                if frame.event == SERVER_EVENTS["TTS_ENDED"]:
                    break

                if frame.event in (SERVER_EVENTS["SESSION_FINISHED"], SERVER_EVENTS["CONNECTION_FINISHED"]):
                    break
        finally:
            delayed_start.cancel()

    if chunks:
        return {"audio": b"".join(chunks), "warnings": warnings}
    if session_started:
        raise ValueError("音色试听没有返回音频。")
    raise ValueError("火山实时语音连接已关闭。")


async def _delayed(seconds: float, callback) -> None:
    await asyncio.sleep(seconds)
    await callback()
