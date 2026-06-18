import { useRef, useState } from "react";
import { decodeBase64Pcm16, encodePcm16, resampleTo16k } from "../lib/audio";
import { DEFAULT_VOICE_PROFILE, VOICE_PROFILES, findVoiceProfile } from "./voiceProfiles";
import "./styles.css";

type Status = "idle" | "connecting" | "connected" | "error";

type ServerEvent =
  | { type: "status"; status: Status; warnings?: string[] }
  | { type: "payload"; payload: unknown; warnings?: string[] }
  | { type: "event"; event: { id: string; type: "user" | "assistant"; text: string; at: string; outputId?: string } }
  | RouteDecision
  | { type: "audio"; data: string; mime: string; outputId?: string }
  | { type: "usage"; usage: Record<string, unknown> }
  | { type: "error"; message: string };

type RouteDecision = {
  type: "route_decision";
  session_id: string;
  turn_id: string;
  agent_profile_id?: string;
  mode: string;
  intent?: string;
  scenario_id?: string;
  scenario_intent?: string;
  confidence: number;
  need_clarification?: boolean;
  requires_confirmation?: boolean;
  arguments?: Record<string, unknown>;
};

type LogItem = {
  id: string;
  role: string;
  text: string;
  at: string;
  outputId?: string;
};

type Metrics = {
  connectedAtMs?: number;
  firstAudioAtMs?: number;
  audioChunks: number;
  userEvents: number;
  assistantEvents: number;
  lastError: string;
};

const emptyMetrics: Metrics = {
  audioChunks: 0,
  userEvents: 0,
  assistantEvents: 0,
  lastError: ""
};

const AGENT_PROFILE_OPTIONS = [
  { id: "default", name: "默认助手" },
  { id: "phone-assistant", name: "手机助理" }
];

export function App() {
  const [status, setStatus] = useState<Status>("idle");
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [textInput, setTextInput] = useState("");
  const [health, setHealth] = useState("unchecked");
  const [metrics, setMetrics] = useState<Metrics>(emptyMetrics);
  const [selectedProfileId, setSelectedProfileId] = useState(DEFAULT_VOICE_PROFILE.id);
  const [selectedAgentProfileId, setSelectedAgentProfileId] = useState("phone-assistant");
  const [routerText, setRouterText] = useState("帮我打开作品页");
  const [routerResult, setRouterResult] = useState<RouteDecision | null>(null);
  const [routerError, setRouterError] = useState("");
  const [routerLoading, setRouterLoading] = useState(false);
  const selectedProfile = findVoiceProfile(selectedProfileId);
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const outputContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef(0);
  const audioUploadReadyRef = useRef(false);
  const callStartedAtRef = useRef<number | null>(null);

  async function checkHealth() {
    try {
      const response = await fetch("/health");
      const data = (await response.json()) as { ok: boolean; volcConfigured: boolean };
      setHealth(data.volcConfigured ? "volc configured" : "missing volc credentials");
    } catch {
      setHealth("api unavailable");
    }
  }

  async function startCall() {
    if (socketRef.current) return;
    resetLogs();
    setStatus("connecting");
    setWarnings([]);
    resetMetrics();
    callStartedAtRef.current = performance.now();
    await checkHealth();

    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/realtime`);
    ws.binaryType = "arraybuffer";
    socketRef.current = ws;

    ws.onopen = async () => {
      const micReady = await startMicrophone(ws);
      if (!micReady) {
        appendLog("system", "麦克风未开启，仍可使用文字输入测试 S2S。");
      }
      ws.send(JSON.stringify({ type: "start", config: selectedProfile.config }));
    };

    ws.onmessage = (message) => {
      const data = JSON.parse(message.data) as ServerEvent;
      handleServerMessage(data);
    };

    ws.onerror = () => {
      markError("本地 S2S 网关连接失败。");
      setStatus("error");
      appendLog("error", "本地 S2S 网关连接失败。");
    };

    ws.onclose = () => {
      socketRef.current = null;
      audioUploadReadyRef.current = false;
      stopMicrophone();
      setStatus("idle");
    };
  }

  function endCall() {
    const ws = socketRef.current;
    socketRef.current = null;
    audioUploadReadyRef.current = false;
    stopMicrophone();
    stopPlayback();
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "finish" }));
      ws.close();
    }
    setStatus("idle");
  }

  function sendText() {
    const text = textInput.trim();
    const ws = socketRef.current;
    if (!text || ws?.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "user_text", text }));
    setTextInput("");
    appendLog("user", text);
  }

  async function testRouter() {
    const text = routerText.trim();
    if (!text || routerLoading) return;

    setRouterLoading(true);
    setRouterError("");

    try {
      const response = await fetch("/semantic-router/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          session_id: "frontend-debug",
          turn_id: `router-${Date.now()}`,
          agent_profile_id: selectedAgentProfileId
        })
      });
      if (!response.ok) {
        throw new Error(`Router API ${response.status}`);
      }
      const decision = (await response.json()) as RouteDecision;
      setRouterResult(decision);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Router 请求失败。";
      setRouterError(message);
    } finally {
      setRouterLoading(false);
    }
  }

  async function startMicrophone(ws: WebSocket) {
    if (!navigator.mediaDevices?.getUserMedia) return false;

    try {
      stopMicrophone();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      const context = new AudioContext();
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(2048, 1, 1);

      processor.onaudioprocess = (event) => {
        if (!audioUploadReadyRef.current || ws.readyState !== WebSocket.OPEN) return;
        const input = event.inputBuffer.getChannelData(0);
        const pcm = encodePcm16(resampleTo16k(input, context.sampleRate));
        if (pcm.byteLength > 0) ws.send(pcm);
      };

      source.connect(processor);
      processor.connect(context.destination);
      streamRef.current = stream;
      inputContextRef.current = context;
      processorRef.current = processor;
      sourceRef.current = source;
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : "麦克风启动失败。";
      markError(message);
      appendLog("error", message);
      return false;
    }
  }

  function stopMicrophone() {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    void inputContextRef.current?.close().catch(() => undefined);
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    inputContextRef.current = null;
  }

  function handleServerMessage(data: ServerEvent) {
    if (data.type === "status") {
      setStatus(data.status);
      audioUploadReadyRef.current = data.status === "connected";
      if (data.status === "connected") markConnected();
      if (data.warnings?.length) setWarnings(data.warnings);
      appendLog("system", `status: ${data.status}`);
      return;
    }

    if (data.type === "payload") {
      if (data.warnings?.length) setWarnings(data.warnings);
      appendLog("system", "StartSession payload 已发送。");
      return;
    }

    if (data.type === "event") {
      markTextEvent(data.event.type);
      appendLog(data.event.type, data.event.text, data.event.outputId);
      return;
    }

    if (data.type === "route_decision") {
      appendLog("route", `${data.mode}.${data.scenario_intent || data.intent || "unknown"}`, data.turn_id);
      return;
    }

    if (data.type === "audio") {
      markAudioChunk();
      playPcm24k(data.data);
      return;
    }

    if (data.type === "usage") {
      appendLog("system", `usage: ${JSON.stringify(data.usage)}`);
      return;
    }

    if (data.type === "error") {
      setStatus("error");
      markError(data.message);
      appendLog("error", data.message);
    }
  }

  function playPcm24k(base64: string) {
    const samples = decodeBase64Pcm16(base64);
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    const context = outputContextRef.current || new AudioContextClass({ sampleRate: 24000 });
    outputContextRef.current = context;

    const buffer = context.createBuffer(1, samples.length, 24000);
    buffer.copyToChannel(samples, 0);
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);

    const startAt = Math.max(context.currentTime, nextPlayTimeRef.current);
    source.start(startAt);
    nextPlayTimeRef.current = startAt + buffer.duration;
  }

  function stopPlayback() {
    void outputContextRef.current?.close().catch(() => undefined);
    outputContextRef.current = null;
    nextPlayTimeRef.current = 0;
  }

  function appendLog(role: string, text: string, outputId?: string) {
    setLogs((items) => {
      if (outputId) {
        const existingIndex = items.findIndex((item) => item.outputId === outputId);
        if (existingIndex >= 0) {
          return items.map((item, index) => (index === existingIndex ? { ...item, text } : item));
        }
      }

      return [
        {
          id: crypto.randomUUID(),
          role,
          text,
          outputId,
          at: new Date().toLocaleTimeString("zh-CN", { hour12: false })
        },
        ...items
      ];
    });
  }

  function resetLogs() {
    setLogs([]);
  }

  function resetMetrics() {
    setMetrics(emptyMetrics);
  }

  function markConnected() {
    const startedAt = callStartedAtRef.current;
    setMetrics((current) => ({
      ...current,
      connectedAtMs: startedAt ? Math.round(performance.now() - startedAt) : undefined
    }));
  }

  function markTextEvent(role: "user" | "assistant") {
    setMetrics((current) => ({
      ...current,
      userEvents: role === "user" ? current.userEvents + 1 : current.userEvents,
      assistantEvents: role === "assistant" ? current.assistantEvents + 1 : current.assistantEvents
    }));
  }

  function markAudioChunk() {
    const startedAt = callStartedAtRef.current;
    setMetrics((current) => ({
      ...current,
      firstAudioAtMs:
        current.firstAudioAtMs ?? (startedAt ? Math.round(performance.now() - startedAt) : undefined),
      audioChunks: current.audioChunks + 1
    }));
  }

  function markError(message: string) {
    setMetrics((current) => ({ ...current, lastError: message }));
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Voice Engine</h1>
          <p>FastAPI + React + 火山端到端实时语音 S2S</p>
        </div>
        <div className={`status status-${status}`}>{status}</div>
      </header>

      <section className="controls">
        <button type="button" onClick={startCall} disabled={status !== "idle"}>
          开始通话
        </button>
        <button type="button" onClick={endCall} disabled={status === "idle"}>
          结束
        </button>
        <button type="button" onClick={checkHealth}>
          检查后端
        </button>
        <span>{health}</span>
      </section>

      <section className="profile-panel">
        <label htmlFor="voice-profile">Voice Profile</label>
        <select
          id="voice-profile"
          value={selectedProfileId}
          onChange={(event) => setSelectedProfileId(event.target.value)}
          disabled={status !== "idle"}
        >
          {VOICE_PROFILES.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.name}
            </option>
          ))}
        </select>
        <span>{selectedProfile.description}</span>
        <span>speaker: {selectedProfile.config.speaker}</span>
      </section>

      <section className="text-input">
        <input
          value={textInput}
          onChange={(event) => setTextInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") sendText();
          }}
          placeholder="也可以输入文字测试 ChatTextQuery"
        />
        <button type="button" onClick={sendText} disabled={status !== "connected" || !textInput.trim()}>
          发送
        </button>
      </section>

      <section className="router-panel">
        <div className="router-heading">
          <h2>Semantic Router</h2>
          <span>{routerResult ? `${routerResult.mode}.${routerResult.scenario_intent || routerResult.intent}` : "ready"}</span>
        </div>
        <div className="router-form">
          <select
            value={selectedAgentProfileId}
            onChange={(event) => setSelectedAgentProfileId(event.target.value)}
            aria-label="Agent Profile"
          >
            {AGENT_PROFILE_OPTIONS.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
          <input
            value={routerText}
            onChange={(event) => setRouterText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void testRouter();
            }}
            placeholder="输入文本测试意图"
          />
          <button type="button" onClick={() => void testRouter()} disabled={routerLoading || !routerText.trim()}>
            {routerLoading ? "识别中" : "识别意图"}
          </button>
        </div>
        {routerError ? <p className="router-error">{routerError}</p> : null}
        {routerResult ? (
          <>
            <dl className="router-summary">
              <div>
                <dt>mode</dt>
                <dd>{routerResult.mode}</dd>
              </div>
              <div>
                <dt>intent</dt>
                <dd>{routerResult.scenario_intent || routerResult.intent || "-"}</dd>
              </div>
              <div>
                <dt>confidence</dt>
                <dd>{routerResult.confidence.toFixed(2)}</dd>
              </div>
              <div>
                <dt>confirm</dt>
                <dd>{routerResult.requires_confirmation ? "true" : "false"}</dd>
              </div>
            </dl>
            <pre className="router-json">{JSON.stringify(routerResult, null, 2)}</pre>
          </>
        ) : null}
      </section>

      {warnings.length ? (
        <section className="warnings">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </section>
      ) : null}

      <section className="metrics-panel">
        <h2>诊断</h2>
        <dl>
          <div>
            <dt>连接耗时</dt>
            <dd>{formatMs(metrics.connectedAtMs)}</dd>
          </div>
          <div>
            <dt>首段音频</dt>
            <dd>{formatMs(metrics.firstAudioAtMs)}</dd>
          </div>
          <div>
            <dt>音频片段</dt>
            <dd>{metrics.audioChunks}</dd>
          </div>
          <div>
            <dt>用户文本</dt>
            <dd>{metrics.userEvents}</dd>
          </div>
          <div>
            <dt>助手文本</dt>
            <dd>{metrics.assistantEvents}</dd>
          </div>
          <div>
            <dt>最近错误</dt>
            <dd>{metrics.lastError || "-"}</dd>
          </div>
        </dl>
      </section>

      <section className="log-panel">
        <h2>事件</h2>
        <ul>
          {logs.map((item) => (
            <li key={item.id} className={`log-item log-${item.role}`}>
              <time>{item.at}</time>
              <strong>{item.role}</strong>
              <span>{item.text}</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

declare global {
  interface Window {
    webkitAudioContext?: typeof AudioContext;
  }
}

function formatMs(value?: number) {
  return typeof value === "number" ? `${value} ms` : "-";
}
