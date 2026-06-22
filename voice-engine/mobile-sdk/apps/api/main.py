from __future__ import annotations

import base64
from typing import Any

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .config import has_volc_credentials, has_volc_podcast_credentials, load_local_env
from .integrations.volc.payload import build_start_session_payload, redact_payload
from .memory.card_service import (
    DEFAULT_MEMORY_MAX_CHARS,
    MAX_MEMORY_MAX_CHARS,
    MIN_MEMORY_MAX_CHARS,
    compress_memory_card,
    delete_memory_card,
    normalize_memory_card,
    read_memory_card,
    to_memory_id,
    write_memory_card,
)
from .realtime.gateway import RealtimeGateway
from .runtime.call_log_service import list_call_logs, save_call_log
from .runtime.config_service import (
    create_role,
    create_scene_runtime_session_config,
    create_scene,
    create_user,
    create_runtime_session_config,
    login_user,
    list_roles,
    list_scenes,
    list_users,
    require_session_user,
    require_user_access,
    update_role,
    update_scene,
    update_user,
    save_scene_config,
)
from .runtime.intent_service import classify_intent
from .runtime.podcast_service import build_podcast_audio_payload, build_podcast_audio_request, build_podcast_draft
from .runtime.podcast_synthesis_service import request_podcast_audio
from .runtime.session_result_service import build_session_audio_wav, get_session_result
from .runtime.embedded_scene_config import EMBEDDED_SCENE_USER_ID
from .runtime.user_profile_service import build_user_profile
from .shared.value_utils import to_int_in_range
from .voice.preview_service import request_voice_preview


load_local_env()

app = FastAPI(title="ai-engine realtime voice API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["content-type", "x-runtime-session"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "volcengine": has_volc_credentials()}


@app.get("/memory-card")
async def get_memory_card(request: Request, userId: str | None = None, sceneId: str | None = None):
    try:
        require_user_access(_get_session_token(request), userId)
        user_id = to_memory_id(userId)
        scene_id = to_memory_id(sceneId)
        card = await read_memory_card(user_id, scene_id)
        return {"card": card, "found": bool(card)}
    except PermissionError as exc:
        return _error_response(403, exc, "无权读取本地压缩记忆。")
    except Exception as exc:
        return _error_response(400, exc, "无法读取本地压缩记忆。")


@app.get("/runtime/users")
async def runtime_users():
    return {"users": list_users()}


@app.post("/runtime/login")
async def runtime_login(request: Request):
    try:
        body = await _read_json(request)
        return login_user(body.get("userId"))
    except Exception as exc:
        return _error_response(400, exc, "无法登录。")


@app.post("/runtime/users")
async def create_runtime_user(request: Request):
    try:
        body = await _read_json(request)
        operator = require_session_user(_get_session_token(request), body.get("operatorUserId"))
        user = create_user(operator["id"], body.get("user"))
        return {"user": user}
    except PermissionError as exc:
        return _error_response(403, exc, "无权创建用户。")
    except Exception as exc:
        return _error_response(400, exc, "无法创建用户。")


@app.put("/runtime/users/{user_id}")
async def update_runtime_user(user_id: str, request: Request):
    try:
        body = await _read_json(request)
        operator = require_session_user(_get_session_token(request), body.get("operatorUserId"))
        user = update_user(operator["id"], user_id, body.get("user"))
        return {"user": user}
    except PermissionError as exc:
        return _error_response(403, exc, "无权修改用户。")
    except Exception as exc:
        return _error_response(400, exc, "无法修改用户。")


@app.get("/runtime/roles")
async def runtime_roles():
    return {"roles": list_roles()}


@app.post("/runtime/roles")
async def create_runtime_role(request: Request):
    try:
        body = await _read_json(request)
        operator = require_session_user(_get_session_token(request), body.get("operatorUserId"))
        role = create_role(operator["id"], body.get("role"))
        return {"role": role}
    except PermissionError as exc:
        return _error_response(403, exc, "无权创建角色。")
    except Exception as exc:
        return _error_response(400, exc, "无法创建角色。")


@app.put("/runtime/roles/{role_id}")
async def update_runtime_role(role_id: str, request: Request):
    try:
        body = await _read_json(request)
        operator = require_session_user(_get_session_token(request), body.get("operatorUserId"))
        role = update_role(operator["id"], role_id, body.get("role"))
        return {"role": role}
    except PermissionError as exc:
        return _error_response(403, exc, "无权修改角色。")
    except Exception as exc:
        return _error_response(400, exc, "无法修改角色。")


@app.get("/runtime/scenes")
async def runtime_scenes(userId: str | None = None):
    try:
        return {"scenes": list_scenes(userId)}
    except Exception as exc:
        return _error_response(400, exc, "无法读取场景列表。")


@app.post("/runtime/scenes")
async def create_runtime_scene(request: Request):
    try:
        body = await _read_json(request)
        operator = _optional_operator(request, body.get("operatorUserId"))
        result = create_scene(operator["id"], body.get("scene"))
        return result
    except PermissionError as exc:
        return _error_response(403, exc, "无权创建场景。")
    except Exception as exc:
        return _error_response(400, exc, "无法创建场景。")


@app.put("/runtime/scenes/{scene_id}")
async def update_runtime_scene(scene_id: str, request: Request):
    try:
        body = await _read_json(request)
        operator = _optional_operator(request, body.get("operatorUserId"))
        scene = update_scene(operator["id"], scene_id, body.get("scene"))
        return {"scene": scene}
    except PermissionError as exc:
        return _error_response(403, exc, "无权修改场景。")
    except Exception as exc:
        return _error_response(400, exc, "无法修改场景。")


@app.post("/runtime/scenes/{scene_id}/config")
async def update_runtime_scene_config(scene_id: str, request: Request):
    try:
        body = await _read_json(request)
        operator = _optional_operator(request, body.get("userId"))
        scene = save_scene_config(scene_id, operator["id"], body.get("config"), body.get("targetUserId"))
        return {"scene": scene}
    except PermissionError as exc:
        return _error_response(403, exc, "无权保存场景配置。")
    except Exception as exc:
        return _error_response(400, exc, "无法保存场景配置。")


@app.post("/runtime/scene-session")
async def runtime_scene_session(request: Request):
    try:
        body = await _read_json(request)
        if body.get("userId"):
            require_user_access(_get_session_token(request), body.get("userId"))
            session = await create_runtime_session_config(
                body.get("userId"),
                body.get("sceneId"),
                memory_enabled=body.get("memoryEnabled", True),
            )
        else:
            session = await create_scene_runtime_session_config(
                body.get("sceneId"),
                memory_enabled=body.get("memoryEnabled", True),
            )
        return session
    except PermissionError as exc:
        return _error_response(403, exc, "当前用户没有被分配这个场景。")
    except Exception as exc:
        return _error_response(400, exc, "无法生成场景会话配置。")


@app.get("/runtime/sessions/{session_id}/result")
async def runtime_session_result(session_id: str):
    try:
        return get_session_result(session_id)
    except Exception as exc:
        return _error_response(404, exc, "无法读取会话结果。")


@app.get("/runtime/sessions/{session_id}/audio")
async def runtime_session_audio(session_id: str, source: str = "client"):
    try:
        wav = build_session_audio_wav(session_id, source=source)
        return Response(content=wav, media_type="audio/wav")
    except Exception as exc:
        return _error_response(404, exc, "无法读取会话录音。")


@app.get("/runtime/call-logs")
async def runtime_call_logs(request: Request, userId: str | None = None, sceneId: str | None = None, limit: int | None = None):
    try:
        operator = require_session_user(_get_session_token(request))
        target_user_id = userId
        if userId:
            require_user_access(_get_session_token(request), userId)
        elif operator["role"] != "admin":
            target_user_id = operator["id"]
        return {"logs": list_call_logs(target_user_id, sceneId, limit or 10)}
    except PermissionError as exc:
        return _error_response(403, exc, "无权读取访谈日志。")
    except Exception as exc:
        return _error_response(400, exc, "无法读取访谈日志。")


@app.post("/runtime/intent")
async def runtime_intent(request: Request):
    try:
        body = await _read_json(request)
        if body.get("userId"):
            require_session_user(_get_session_token(request), body.get("userId"))
        return {"result": classify_intent(body.get("text"))}
    except PermissionError as exc:
        return _error_response(403, exc, "无权识别该用户意图。")
    except Exception as exc:
        return _error_response(400, exc, "无法识别对话意图。")


@app.post("/runtime/podcast/draft")
async def runtime_podcast_draft(request: Request):
    try:
        body = await _read_json(request)
        if body.get("userId"):
            require_session_user(_get_session_token(request), body.get("userId"))
        return {"draft": build_podcast_draft(body)}
    except PermissionError as exc:
        return _error_response(403, exc, "无权生成该用户播客草稿。")
    except Exception as exc:
        return _error_response(400, exc, "无法生成播客草稿。")


@app.post("/runtime/podcast/audio")
async def runtime_podcast_audio(request: Request):
    try:
        body = await _read_json(request)
        if body.get("userId"):
            require_session_user(_get_session_token(request), body.get("userId"))
        if not has_volc_podcast_credentials():
            return {"audio": build_podcast_audio_request(body, configured=False)}
        return {"audio": await request_podcast_audio(build_podcast_audio_payload(body))}
    except PermissionError as exc:
        return _error_response(403, exc, "无权生成该用户播客音频。")
    except Exception as exc:
        return _error_response(400, exc, "无法生成播客音频。")


@app.get("/runtime/user-profile")
async def runtime_user_profile(request: Request, userId: str | None = None, sceneId: str | None = None):
    try:
        if not userId:
            raise ValueError("userId 不能为空。")
        require_user_access(_get_session_token(request), userId)
        return {"profile": build_user_profile(userId, sceneId)}
    except PermissionError as exc:
        return _error_response(403, exc, "无权读取用户画像。")
    except Exception as exc:
        return _error_response(400, exc, "无法读取用户画像。")


@app.post("/runtime/call-logs")
async def create_runtime_call_log(request: Request):
    try:
        body = await _read_json(request)
        if not _is_embedded_scene_call_log(body):
            require_session_user(_get_session_token(request), body.get("userId"))
        log = save_call_log(body)
        return {"log": log}
    except PermissionError as exc:
        return _error_response(403, exc, "无权保存访谈日志。")
    except Exception as exc:
        return _error_response(400, exc, "无法保存访谈日志。")


@app.delete("/memory-card")
async def remove_memory_card(request: Request, userId: str | None = None, sceneId: str | None = None):
    try:
        require_user_access(_get_session_token(request), userId)
        user_id = to_memory_id(userId)
        scene_id = to_memory_id(sceneId)
        await delete_memory_card(user_id, scene_id)
        return {"ok": True}
    except PermissionError as exc:
        return _error_response(403, exc, "无权清空本地压缩记忆。")
    except Exception as exc:
        return _error_response(400, exc, "无法清空本地压缩记忆。")


@app.post("/memory-card/compress")
async def compress_card(request: Request):
    try:
        body = await _read_json(request)
        require_session_user(_get_session_token(request), body.get("userId"))
        user_id = to_memory_id(body.get("userId"))
        scene_id = to_memory_id(body.get("sceneId"))
        max_chars = to_int_in_range(body.get("maxChars"), DEFAULT_MEMORY_MAX_CHARS, MIN_MEMORY_MAX_CHARS, MAX_MEMORY_MAX_CHARS)
        stored_card = await read_memory_card(user_id, scene_id)
        previous_card = stored_card or normalize_memory_card(body.get("previousCard"), user_id, scene_id, max_chars)
        result = compress_memory_card(
            user_id=user_id,
            scene_id=scene_id,
            max_chars=max_chars,
            previous_card=previous_card,
            report=body.get("report") or {},
        )

        await write_memory_card(result["card"])
        return {
            "card": result["card"],
            "source": "local-deterministic",
            "warnings": result["warnings"],
        }
    except Exception as exc:
        return _error_response(400, exc, "无法压缩本地记忆。")


@app.post("/payload-preview")
async def payload_preview(request: Request):
    try:
        body = await _read_json(request)
        session = build_start_session_payload(body.get("config") or {})
        warnings = session["warnings"]
        return {
            "mode": "volcengine",
            "payload": redact_payload(session["payload"]),
            "warnings": warnings
            if has_volc_credentials()
            else [
                *warnings,
                "缺少火山实时语音真实链路配置：请在 apps/api/.local/env/.env.local 中配置 VOLC_API_APP_ID 和 VOLC_API_ACCESS_KEY。",
            ],
        }
    except Exception as exc:
        return _error_response(400, exc, "无法生成 API 调用参数。")


@app.post("/voice-preview")
async def voice_preview(request: Request):
    try:
        body = await _read_json(request)
        preview = await request_voice_preview(body.get("config") or {}, body.get("text"))
        return {
            "mode": "volcengine",
            "mime": "audio/pcm; format=s16le; rate=24000",
            "data": base64.b64encode(preview["audio"]).decode("ascii"),
            "warnings": preview["warnings"],
        }
    except Exception as exc:
        return _error_response(502 if has_volc_credentials() else 400, exc, "无法生成音色试听。")


@app.websocket("/realtime")
async def realtime(websocket: WebSocket):
    await RealtimeGateway(websocket).run()


async def _read_json(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception as exc:
        raise ValueError("无法解析 JSON 请求体。") from exc
    if not isinstance(body, dict):
        raise ValueError("无法解析 JSON 请求体。")
    return body


def _get_session_token(request: Request) -> str | None:
    return request.headers.get("x-runtime-session")


def _is_embedded_scene_call_log(body: dict[str, Any]) -> bool:
    if str(body.get("userId") or "").strip() != EMBEDDED_SCENE_USER_ID:
        return False
    return all(str(body.get(key) or "").strip() for key in ("requestId", "sessionId", "sceneId"))


def _optional_operator(request: Request, operator_user_id: Any | None = None) -> dict[str, Any]:
    token = _get_session_token(request)
    if token:
        return require_session_user(token, operator_user_id)
    return {"id": "admin_operator"}


def _error_response(status_code: int, error: Exception, fallback: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": str(error) or fallback})
