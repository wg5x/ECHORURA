import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Headphones, ListChecks, Phone, RefreshCw, Send } from "lucide-react";
import { buildPlatformInterviewUrl, resolveAppRoute, shouldMountPlatformFrame } from "./appRoutes";
import "./styles.css";

type EntryParams = {
  name: string;
  phone: string;
  city: string;
};

type BusinessRequest = {
  requestId: string;
  sceneKind: string;
  sceneId: string;
  entryParams: EntryParams;
  platformSessionId: string | null;
  status: "created" | "started" | "finished" | "failed";
  createdAt: string;
  updatedAt: string;
};

type SessionResult = {
  sessionId: string;
  requestId?: string | null;
  sceneId?: string | null;
  status: string;
  startedAt?: string | null;
  endedAt?: string | null;
  transcript: Array<{ role: "user" | "assistant"; text: string; at: string }>;
  audio: { url: string; mime: string; source: string; byteLength?: number | null } | null;
};

const businessApiBase = import.meta.env.VITE_BUSINESS_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8788";
const platformBase = import.meta.env.VITE_PLATFORM_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:5175";
const platformApiBase = import.meta.env.VITE_PLATFORM_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8787";

function App() {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const pendingStartRequestIdRef = useRef<string | null>(null);
  const appRoute = resolveAppRoute(window.location.pathname, import.meta.env.BASE_URL);
  const [entryParams, setEntryParams] = useState<EntryParams>({ name: "", phone: "", city: "" });
  const [requests, setRequests] = useState<BusinessRequest[]>([]);
  const [activeRequest, setActiveRequest] = useState<BusinessRequest | null>(null);
  const [sessionResult, setSessionResult] = useState<SessionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const platformUrl = useMemo(() => {
    return buildPlatformInterviewUrl(platformBase, activeRequest?.requestId);
  }, [activeRequest?.requestId]);
  const platformFrameVisible = shouldMountPlatformFrame(activeRequest?.requestId);

  useEffect(() => {
    if (appRoute === "admin") void loadRequests();
  }, [appRoute]);

  useEffect(() => {
    function handlePlatformMessage(event: MessageEvent) {
      const message = event.data;
      if (!message || typeof message !== "object") return;
      if (message.type === "ai-engine:ready") {
        const requestId = pendingStartRequestIdRef.current;
        if (requestId) {
          iframeRef.current?.contentWindow?.postMessage({ type: "ai-engine:start", requestId }, platformBase);
          pendingStartRequestIdRef.current = null;
        }
      }
      if (message.type === "ai-engine:started" && typeof message.sessionId === "string") {
        void markRequest(message.requestId || activeRequest?.requestId, {
          platformSessionId: message.sessionId,
          status: "started",
        });
      }
      if (message.type === "ai-engine:finished" && typeof message.sessionId === "string") {
        void markRequest(message.requestId || activeRequest?.requestId, {
          platformSessionId: message.sessionId,
          status: "finished",
        }).then(() => loadSessionResult(message.sessionId));
      }
      if (message.type === "ai-engine:error") {
        setError(typeof message.message === "string" ? message.message : "平台会话异常。");
        void markRequest(message.requestId || activeRequest?.requestId, {
          platformSessionId: typeof message.sessionId === "string" ? message.sessionId : undefined,
          status: "failed",
        });
      }
    }

    window.addEventListener("message", handlePlatformMessage);
    return () => window.removeEventListener("message", handlePlatformMessage);
  }, [activeRequest?.requestId]);

  async function loadRequests() {
    const response = await fetch(`${businessApiBase}/api/requests`);
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "无法读取访谈列表。");
    setRequests(body.requests);
  }

  async function createBusinessRequest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSessionResult(null);
    try {
      const response = await fetch(`${businessApiBase}/api/requests`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ entryParams }),
      });
      const request = await response.json();
      if (!response.ok) throw new Error(request.error || "无法创建访谈请求。");
      setActiveRequest(request);
      pendingStartRequestIdRef.current = request.requestId;
      setRequests((current) => [request, ...current]);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "无法创建访谈请求。");
    } finally {
      setLoading(false);
    }
  }

  async function markRequest(requestId: unknown, patch: { platformSessionId?: string; status: BusinessRequest["status"] }) {
    if (typeof requestId !== "string") return null;
    const response = await fetch(`${businessApiBase}/api/requests/${requestId}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(patch),
    });
    const request = await response.json();
    if (!response.ok) throw new Error(request.error || "无法更新访谈请求。");
    setRequests((current) => current.map((item) => (item.requestId === request.requestId ? request : item)));
    setActiveRequest((current) => (current?.requestId === request.requestId ? request : current));
    return request as BusinessRequest;
  }

  async function loadSessionResult(sessionId: string) {
    const response = await fetch(`${platformApiBase}/runtime/sessions/${sessionId}/result`);
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "无法读取平台会话结果。");
    setSessionResult(body);
  }

  function selectRequest(request: BusinessRequest) {
    setActiveRequest(request);
    setError(null);
    if (request.platformSessionId) {
      void loadSessionResult(request.platformSessionId);
    } else {
      setSessionResult(null);
    }
  }

  if (appRoute === "admin") {
    return (
      <main className="shell admin-shell">
        <section className="panel list-panel">
          <div className="panel-title">
            <ListChecks size={18} />
            <span>访谈列表</span>
            <button className="ghost" type="button" onClick={() => void loadRequests()}>
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="request-list">
            {requests.map((request) => (
              <button
                key={request.requestId}
                className={activeRequest?.requestId === request.requestId ? "request-item active" : "request-item"}
                type="button"
                onClick={() => selectRequest(request)}
              >
                <strong>{request.entryParams.name}</strong>
                <span>{request.entryParams.city} / {request.entryParams.phone}</span>
                <small>{request.status} · {request.requestId}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="panel detail-panel">
          <div className="panel-title">
            <Headphones size={18} />
            <span>访谈详情</span>
          </div>
          {activeRequest ? (
            <div className="detail-meta">
              <strong>{activeRequest.entryParams.name}</strong>
              <span>{activeRequest.entryParams.city} / {activeRequest.entryParams.phone}</span>
              <small>{activeRequest.platformSessionId || "暂无平台 sessionId"}</small>
            </div>
          ) : null}
          {sessionResult?.audio ? (
            <audio controls src={`${platformApiBase}${sessionResult.audio.url}`} />
          ) : (
            <p className="empty">访谈完成并开启录音后，这里会显示播放器。</p>
          )}
          <div className="transcript-list">
            {sessionResult?.transcript.length ? (
              sessionResult.transcript.map((item, index) => (
                <article className={item.role} key={`${item.at}-${index}`}>
                  <small>{item.role === "user" ? "用户" : "助手"} · {item.at}</small>
                  <p>{item.text}</p>
                </article>
              ))
            ) : (
              <p className="empty">访谈完成后，这里会显示对话内容。</p>
            )}
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell interview-shell">
      <section className="panel entry-panel">
        <div className="panel-title">
          <Phone size={18} />
          <span>访谈入口</span>
        </div>
        <form onSubmit={createBusinessRequest}>
          <label>
            姓名
            <input value={entryParams.name} onChange={(event) => setEntryParams({ ...entryParams, name: event.target.value })} required />
          </label>
          <label>
            电话
            <input value={entryParams.phone} onChange={(event) => setEntryParams({ ...entryParams, phone: event.target.value })} required />
          </label>
          <label>
            城市
            <input value={entryParams.city} onChange={(event) => setEntryParams({ ...entryParams, city: event.target.value })} required />
          </label>
          <button type="submit" disabled={loading}>
            <Send size={16} />
            创建并开始访谈
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="panel iframe-panel">
        {platformFrameVisible ? (
          <iframe ref={iframeRef} title="AI Engine 平台访谈" src={platformUrl} allow="microphone; autoplay" />
        ) : (
          <div className="iframe-empty">
            <strong>待创建访谈</strong>
            <span>点击“创建并开始访谈”后，这里会自动打开访谈页面。</span>
          </div>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
