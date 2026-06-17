import { useRef, useState } from "react";
import { decodeBase64Pcm16, encodePcm16, resampleTo16k } from "../lib/audio";
import "./styles.css";

type Status = "idle" | "connecting" | "connected" | "error";

type ServerEvent =
  | { type: "status"; status: Status; warnings?: string[] }
  | { type: "payload"; payload: unknown; warnings?: string[] }
  | { type: "event"; event: { id: string; type: "user" | "assistant"; text: string; at: string; outputId?: string } }
  | { type: "audio"; data: string; mime: string; outputId?: string }
  | { type: "usage"; usage: Record<string, unknown> }
  | { type: "error"; message: string };

type LogItem = {
  id: string;
  role: string;
  text: string;
  at: string;
  outputId?: string;
};

const defaultConfig = {
  mode: "o2",
  botName: "ECHORURA",
  speaker: "zh_female_vv_jupiter_bigtts",
  systemRole: "你是 ECHORURA 的语音入口助手。先用简短中文自然对话，支持唱歌请求和联网搜索。",
  speakingStyle: "表达自然、简短、友好。优先一句话回答。",
  openingLine: "你好，我是 ECHORURA。你可以和我语音对话，也可以让我唱歌或联网搜索。",
  enableWebSearch: true,
  enableMusic: true
};

export function App() {
  const [status, setStatus] = useState<Status>("idle");
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [textInput, setTextInput] = useState("");
  const [health, setHealth] = useState("unchecked");
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const outputContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef(0);
  const audioUploadReadyRef = useRef(false);

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
    await checkHealth();

    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/realtime`);
    ws.binaryType = "arraybuffer";
    socketRef.current = ws;

    ws.onopen = async () => {
      const micReady = await startMicrophone(ws);
      if (!micReady) {
        appendLog("system", "麦克风未开启，仍可使用文字输入测试 S2S。");
      }
      ws.send(JSON.stringify({ type: "start", config: defaultConfig }));
    };

    ws.onmessage = (message) => {
      const data = JSON.parse(message.data) as ServerEvent;
      handleServerMessage(data);
    };

    ws.onerror = () => {
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
      appendLog("error", error instanceof Error ? error.message : "麦克风启动失败。");
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
      appendLog(data.event.type, data.event.text, data.event.outputId);
      return;
    }

    if (data.type === "audio") {
      playPcm24k(data.data);
      return;
    }

    if (data.type === "usage") {
      appendLog("system", `usage: ${JSON.stringify(data.usage)}`);
      return;
    }

    if (data.type === "error") {
      setStatus("error");
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

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>ECHORURA Voice Engine</h1>
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

      {warnings.length ? (
        <section className="warnings">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </section>
      ) : null}

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
