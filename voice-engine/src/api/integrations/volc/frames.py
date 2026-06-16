from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from typing import Any


@dataclass
class ServerFrame:
    code: int | None
    event: int | None
    message_type: int
    session_id: str
    payload: Any


def make_json_frame(event_id: int, payload: Any, session_id: str | None = None) -> bytes:
    payload_buffer = json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    parts = [_write_int32(event_id)]

    if session_id:
        session_buffer = session_id.encode("utf-8")
        parts.extend((_write_int32(len(session_buffer)), session_buffer))

    return b"".join([bytes([0x11, 0x14, 0x10, 0x00]), *parts, _write_int32(len(payload_buffer)), payload_buffer])


def make_audio_frame(event_id: int, payload_buffer: bytes, session_id: str | None = None) -> bytes:
    parts = [_write_int32(event_id)]

    if session_id:
        session_buffer = session_id.encode("utf-8")
        parts.extend((_write_int32(len(session_buffer)), session_buffer))

    return b"".join([bytes([0x11, 0x24, 0x00, 0x00]), *parts, _write_int32(len(payload_buffer)), payload_buffer])


def parse_server_frame(data: bytes | str) -> ServerFrame | None:
    buffer = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    if len(buffer) < 8:
        return None

    header_size = (buffer[0] & 0x0F) * 4
    message_type = buffer[1] >> 4
    flags = buffer[1] & 0x0F
    serialization = buffer[2] >> 4
    offset = header_size
    code = None
    event = None

    if message_type == 0x0F:
        code = _read_int32(buffer, offset)
        offset += 4

    if flags in (0x04, 0x05, 0x06, 0x07):
        event = _read_int32(buffer, offset)
        offset += 4

    candidates: list[dict[str, int | str]] = []
    direct_payload_size = _read_int32(buffer, offset)
    if direct_payload_size is not None:
        candidates.append({"session_id": "", "payload_offset": offset + 4, "payload_size": direct_payload_size})

    session_id_size = _read_int32(buffer, offset)
    if session_id_size and 0 < session_id_size < 256 and offset + 4 + session_id_size + 4 <= len(buffer):
        session_id = buffer[offset + 4 : offset + 4 + session_id_size].decode("utf-8")
        payload_size = _read_int32(buffer, offset + 4 + session_id_size)
        if payload_size is not None:
            candidates.insert(
                0,
                {
                    "session_id": session_id,
                    "payload_offset": offset + 4 + session_id_size + 4,
                    "payload_size": payload_size,
                },
            )

    for candidate in candidates:
        payload_offset = int(candidate["payload_offset"])
        payload_size = int(candidate["payload_size"])
        if payload_size < 0 or payload_offset + payload_size > len(buffer):
            continue

        payload_buffer = buffer[payload_offset : payload_offset + payload_size]
        session_id = str(candidate["session_id"])
        if message_type == 0x0B or serialization == 0x00:
            return ServerFrame(code=code, event=event, message_type=message_type, session_id=session_id, payload=payload_buffer)

        text = payload_buffer.decode("utf-8")
        try:
            payload = json.loads(text) if text else {}
        except json.JSONDecodeError:
            payload = text

        return ServerFrame(code=code, event=event, message_type=message_type, session_id=session_id, payload=payload)

    return ServerFrame(code=code, event=event, message_type=message_type, session_id="", payload=None)


def _write_int32(value: int) -> bytes:
    return struct.pack(">i", value)


def _read_int32(buffer: bytes, offset: int) -> int | None:
    if offset + 4 > len(buffer):
        return None
    return struct.unpack_from(">i", buffer, offset)[0]
