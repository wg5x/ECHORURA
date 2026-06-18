from __future__ import annotations

from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .config import has_volc_credentials, load_local_env
from .realtime.gateway import RealtimeGateway
from .semantic_router import SemanticRouter


load_local_env()

app = FastAPI(title="Voice Engine S2S API")
semantic_router = SemanticRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"ok": True, "volcConfigured": has_volc_credentials()}


@app.post("/semantic-router/decide")
async def decide_route(payload: dict[str, Any]):
    text = str(payload.get("text") or "").strip()
    session_id = str(payload.get("session_id") or "debug-session")
    turn_id = str(payload.get("turn_id") or "turn-1")
    agent_profile_id = str(payload.get("agent_profile_id") or "default")
    return semantic_router.route_text(
        session_id=session_id,
        turn_id=turn_id,
        text=text,
        source="manual_text",
        agent_profile_id=agent_profile_id,
    )


@app.websocket("/realtime")
async def realtime(websocket: WebSocket):
    await RealtimeGateway(websocket).run()
