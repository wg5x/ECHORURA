from __future__ import annotations

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .config import has_volc_credentials, load_local_env
from .realtime.gateway import RealtimeGateway


load_local_env()

app = FastAPI(title="ECHORURA Voice Engine S2S API")

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


@app.websocket("/realtime")
async def realtime(websocket: WebSocket):
    await RealtimeGateway(websocket).run()
