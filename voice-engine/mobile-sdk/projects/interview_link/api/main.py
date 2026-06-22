from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .request_store import create_request, list_requests, update_request


app = FastAPI(title="interview-link business API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["content-type"],
)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/requests")
async def api_list_requests() -> dict[str, Any]:
    return {"requests": list_requests()}


@app.post("/api/requests")
async def api_create_request(request: Request):
    try:
        body = await request.json()
        return create_request(body.get("entryParams"))
    except Exception as exc:
        return _error_response(400, exc, "无法创建访谈请求。")


@app.patch("/api/requests/{request_id}")
async def api_update_request(request_id: str, request: Request):
    try:
        body = await request.json()
        return update_request(request_id, body)
    except KeyError as exc:
        return _error_response(404, exc, "访谈请求不存在。")
    except Exception as exc:
        return _error_response(400, exc, "无法更新访谈请求。")


def _error_response(status_code: int, error: Exception, fallback: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": str(error) or fallback})
