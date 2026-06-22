import React, { useEffect, useMemo, useRef, useState } from "react";
import { ExternalLink, Keyboard, Link2, Phone, Send, X } from "lucide-react";
import { ApiDrawer } from "../components/ApiDrawer";
import { AvatarRing } from "../components/AvatarRing";
import { CallControls } from "../components/CallControls";
import { CallReportCard } from "../components/CallReportCard";
import { ConversationCanvas } from "../components/ConversationCanvas";
import { HeaderBar } from "../components/HeaderBar";
import { AdminDashboard } from "../components/AdminDashboard";
import { PodcastStudio } from "../components/PodcastStudio";
import { DEFAULT_PODCAST_PROFILE } from "../domain/podcast/podcastConfig";
import {
  buildSceneApplicationUrl,
  createSceneApplicationForm,
  getSceneKindLabel,
  SCENE_APPLICATION_CONFIG,
  type SceneApplicationForm,
} from "../domain/scene/sceneApplication";
import { EMBEDDED_SCENE_USER_ID } from "../domain/scene/embeddedSceneConfig";
import { isPodcastScene } from "../domain/scene/sceneKindConfig";
import { sceneTemplates, type SceneTemplate } from "../domain/scene/sceneTemplates";
import {
  buildScenePath,
  canStartPlatformSession,
  DEFAULT_PLATFORM_ROUTE_OPTIONS,
  getSceneListRedirectPath,
  isSceneListRoute,
  parsePlatformRouteOptions,
  resolveSceneRoute,
  shouldShowManualStartButton,
  shouldShowScenePicker,
  shouldShowTextComposer,
  type PlatformRouteOptions,
  type SceneApplicationParams,
} from "../domain/scene/sceneRoutes";
import {
  getLocalAvatarVideoUrl,
  getModeVoiceOptions,
  getModel,
  getSpeaker,
  getVoiceLabel,
  getVoiceOption,
} from "../domain/voice/voiceOptions";
import { appendDisplayEvent, appendTranscriptEvent, buildCallReport } from "../features/call/callSession";
import { encodePcm16, resampleTo16k } from "../lib/audioUtils";
import {
  createBargeInSnapshot,
  defaultBargeInConfig,
  markBargeInInterrupted,
  markBargeInRecovering,
  observeBargeInAudio,
  resetBargeInSnapshot,
  shouldConfirmBargeInFromAsr,
} from "../lib/bargeIn";
import { getBackendBaseUrl, getBackendWsUrl } from "../lib/backend";
import { formatVoiceEventText } from "../lib/eventUtils";
import { createClientId } from "../lib/id";
import { getMemoryCardPreviewItems, hasMemoryCardContent } from "../lib/memoryUtils";
import {
  createRuntimeScene,
  fetchRuntimeCallLogs,
  fetchRuntimeScenes,
  jsonHeaders,
  saveRuntimeCallLog,
  saveRuntimeSceneConfig,
  updateRuntimeScene,
} from "../lib/runtimeApi";
import type {
  CallReport,
  CallLogEntry,
  CreateSceneInput,
  MemoryCard,
  MemoryStatus,
  PayloadPreview,
  RuntimeMetrics,
  ServerMessage,
  VoicePreviewResponse,
} from "./types";
import type { CallStatus, RealtimeConfig, VoiceEvent } from "@ai-engine/shared";
import "../styles/app.css";

const ASSISTANT_AUDIO_ACTIVE_GRACE_MS = 1400;
const AUTO_INTERRUPT_RELEASE_MS = 4000;
const PLAYBACK_START_LEAD_SECONDS = 0.12;
const PLAYBACK_CONTINUATION_LEAD_SECONDS = 0.02;
const PLAYBACK_PREROLL_SECONDS = 0.1;
const PLAYBACK_UNLOCK_SECONDS = 0.02;
const PLAYBACK_LOG_PREFIX = "[AI-ENGINE-PLAYBACK]";
const ANDROID_MICROPHONE_PERMISSION_EVENT = "ai-engine-android-microphone-permission";
const MICROPHONE_RETRY_DELAY_MS = 300;

type PendingPlaybackChunk = {
  binary: string;
  byteLength: number;
  interArrivalMs: number | null;
  outputId?: string;
  receivedAtMs: number;
  sampleCount: number;
  sequence: number;
};

type AndroidBridge = {
  hasMicrophonePermission?: () => boolean;
  requestMicrophonePermission?: () => void;
  openAppSettings?: () => void;
};

declare global {
  interface Window {
    AiEngineAndroid?: AndroidBridge;
  }
}

function getAsrEventText(text: string) {
  return text.replace(/^ASRResponse:\s*/, "");
}

function getAssistantEventText(text: string) {
  return text.replace(/^ChatResponse:\s*/, "");
}

function isVisibleSystemEvent(event: VoiceEvent) {
  return event.type !== "system" || !event.text.startsWith("Interrupt:");
}

function getMicrophoneFailureText(error: unknown) {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError" || error.name === "SecurityError") {
      return "麦克风权限未开启，无法开始真实语音通话。请允许应用使用麦克风后再试。";
    }
    if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
      return "没有检测到可用麦克风，无法开始真实语音通话。";
    }
    if (error.name === "NotReadableError" || error.name === "TrackStartError") {
      return "麦克风暂时不可用，可能被其他应用占用。请关闭占用麦克风的应用后再试。";
    }
  }

  return "麦克风启动失败，无法开始真实语音通话。请检查系统麦克风权限后再试。";
}

function getMicrophoneFailureDetail(error: unknown) {
  if (error instanceof DOMException) {
    return `${error.name}${error.message ? `: ${error.message}` : ""}`;
  }
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return String(error);
}

function isRecoverableMicrophoneStartError(error: unknown) {
  return (
    error instanceof DOMException &&
    (error.name === "NotReadableError" || error.name === "TrackStartError")
  );
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function postParentMessage(type: string, payload: Record<string, unknown> = {}) {
  if (window.parent === window) return;
  window.parent.postMessage({ type, ...payload }, "*");
}

function getScenePreviewMedia(scene: SceneTemplate) {
  const voice = getVoiceOption(scene.config);
  return {
    posterUrl: voice?.avatarPosterUrl,
    videoUrl: voice?.avatarVideoUrl ?? getLocalAvatarVideoUrl("generated/o2-vivi.mp4"),
  };
}

function canPlayHoverPreview() {
  return window.matchMedia?.("(hover: hover) and (pointer: fine)").matches ?? false;
}

function playScenePreviewVideo(card: HTMLElement) {
  if (!canPlayHoverPreview()) return;
  const video = card.querySelector("video");
  if (!video) return;
  void video.play().catch(() => undefined);
}

function resetScenePreviewVideo(card: HTMLElement) {
  const video = card.querySelector("video");
  if (!video) return;
  video.pause();
  video.currentTime = 0;
}

async function getAudioInputSummary() {
  try {
    if (!navigator.mediaDevices?.enumerateDevices) {
      return "enumerateDevices unavailable";
    }

    const devices = await navigator.mediaDevices.enumerateDevices();
    const audioInputs = devices.filter((device) => device.kind === "audioinput");
    if (!audioInputs.length) {
      return "audioinput=0";
    }

    return audioInputs
      .map((device, index) => `${index + 1}:${device.label || "unlabeled"}:${device.deviceId ? "id" : "no-id"}`)
      .join(", ");
  } catch (error) {
    return `enumerateDevices failed: ${getMicrophoneFailureDetail(error)}`;
  }
}

function requestAndroidMicrophonePermission() {
  const bridge = window.AiEngineAndroid;
  const requestMicrophonePermission = bridge?.requestMicrophonePermission;
  if (!requestMicrophonePermission) {
    return Promise.resolve(true);
  }

  try {
    if (bridge.hasMicrophonePermission?.()) {
      return Promise.resolve(true);
    }
  } catch {
    return Promise.resolve(true);
  }

  return new Promise<boolean>((resolve) => {
    let settled = false;
    let timeout = 0;
    const cleanup = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeout);
      window.removeEventListener(ANDROID_MICROPHONE_PERMISSION_EVENT, handlePermissionResult);
    };
    const handlePermissionResult = (event: Event) => {
      const detail = (event as CustomEvent<{ granted?: boolean }>).detail;
      cleanup();
      resolve(Boolean(detail?.granted));
    };
    timeout = window.setTimeout(() => {
      cleanup();
      resolve(false);
    }, 15000);

    window.addEventListener(ANDROID_MICROPHONE_PERMISSION_EVENT, handlePermissionResult);
    try {
      requestMicrophonePermission();
    } catch {
      cleanup();
      resolve(false);
    }
  });
}

export function App() {
  const initialPathname = getSceneListRedirectPath(window.location.pathname) ?? window.location.pathname;
  const initialSceneListOpen = isSceneListRoute(initialPathname);
  const initialRouteMatch = initialSceneListOpen
    ? null
    : resolveSceneRoute(initialPathname, window.location.search, sceneTemplates);
  const fallbackScene = initialRouteMatch?.scene ?? sceneTemplates[0];
  const initialPlatformOptions = parsePlatformRouteOptions(window.location.search);
  const [status, setStatus] = useState<CallStatus>("idle");
  const [events, setEvents] = useState<VoiceEvent[]>([]);
  const [draft, setDraft] = useState("");
  const [assistantTitle, setAssistantTitle] = useState("你好。");
  const [assistantLine, setAssistantLine] = useState("你好呀，今天过得怎么样");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [tokens, setTokens] = useState<number | null>(null);
  const [showTranscript, setShowTranscript] = useState(initialPlatformOptions.showTranscript);
  const [microphoneEnabled, setMicrophoneEnabled] = useState(true);
  const [platformOptions, setPlatformOptions] = useState<PlatformRouteOptions>(initialPlatformOptions);
  const [runtimeScenes, setRuntimeScenes] = useState<SceneTemplate[]>(sceneTemplates);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [selectedSceneId, setSelectedSceneId] = useState<SceneTemplate["id"]>(fallbackScene.id);
  const [config, setConfig] = useState<RealtimeConfig>(fallbackScene.config);
  const [configDirty, setConfigDirty] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [configSaveError, setConfigSaveError] = useState<string | null>(null);
  const [sceneListOpen, setSceneListOpen] = useState(initialSceneListOpen);
  const [sceneManagementOpen, setSceneManagementOpen] = useState(false);
  const [apiDrawerOpen, setApiDrawerOpen] = useState(false);
  const [apiPreview, setApiPreview] = useState<PayloadPreview | null>(null);
  const [connectionMode, setConnectionMode] = useState<"volcengine" | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [voicePreviewing, setVoicePreviewing] = useState(false);
  const [callReport, setCallReport] = useState<CallReport | null>(null);
  const [callLogs, setCallLogs] = useState<CallLogEntry[]>([]);
  const [callLogStatus, setCallLogStatus] = useState<"idle" | "loading" | "saving" | "saved" | "error">("idle");
  const [callLogError, setCallLogError] = useState<string | null>(null);
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const [memoryAutoCompress, setMemoryAutoCompress] = useState(true);
  const [memoryMaxChars, setMemoryMaxChars] = useState(1200);
  const [memoryCard, setMemoryCard] = useState<MemoryCard | null>(null);
  const [memoryStatus, setMemoryStatus] = useState<MemoryStatus>("idle");
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [memoryWarnings, setMemoryWarnings] = useState<string[]>([]);
  const [applicationForm, setApplicationForm] = useState<SceneApplicationForm | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const micSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const playbackSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const nextPlaybackTimeRef = useRef(0);
  const pendingPlaybackChunksRef = useRef<Map<string, PendingPlaybackChunk[]>>(new Map());
  const playbackPrebufferTimersRef = useRef<Map<string, number>>(new Map());
  const prebufferedOutputIdsRef = useRef<Set<string>>(new Set());
  const playbackChunkSequenceRef = useRef(0);
  const lastPlaybackChunkReceivedAtRef = useRef<number | null>(null);
  const audioUploadReadyRef = useRef(false);
  const statusRef = useRef<CallStatus>("idle");
  const silenceTimerRef = useRef<number | null>(null);
  const autoInterruptReleaseTimerRef = useRef<number | null>(null);
  const localBargeInCandidateAtRef = useRef<number | null>(null);
  const bargeInRef = useRef(createBargeInSnapshot());
  const bargeInEnabledRef = useRef(true);
  const showTranscriptRef = useRef(initialPlatformOptions.showTranscript);
  const microphoneEnabledRef = useRef(true);
  const playbackMutedRef = useRef(false);
  const latestAssistantSpeechRef = useRef("");
  const activeAssistantOutputIdRef = useRef<string | null>(null);
  const activeAssistantOutputIdsRef = useRef<Set<string>>(new Set());
  const discardedAssistantOutputIdsRef = useRef<Set<string>>(new Set());
  const assistantAudioActiveUntilRef = useRef(0);
  const forceNextAssistantTurnRef = useRef(false);
  const eventsRef = useRef<VoiceEvent[]>([]);
  const transcriptEventsRef = useRef<VoiceEvent[]>([]);
  const tokensRef = useRef<number | null>(null);
  const activeSceneRef = useRef<SceneTemplate>(fallbackScene);
  const platformOptionsRef = useRef<PlatformRouteOptions>(initialPlatformOptions);
  const platformSessionIdRef = useRef<string | null>(null);
  const sessionStartedAtRef = useRef<number | null>(null);
  const sessionStartedAtLabelRef = useRef("");
  const metricsRef = useRef<RuntimeMetrics | null>(null);
  const reportFinalizedRef = useRef(false);
  const sessionConnectedRef = useRef(false);
  const memoryCardRef = useRef<MemoryCard | null>(null);
  const memoryAutoCompressRef = useRef(true);
  const memoryMaxCharsRef = useRef(1200);
  const selectedSceneIdRef = useRef<SceneTemplate["id"]>(fallbackScene.id);
  const connectRef = useRef<() => Promise<void>>(async () => undefined);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      stopSilenceKeepAlive();
      clearAutoInterruptReleaseTimer();
      stopMicrophone();
      stopPlayback({ closeContext: true });
    };
  }, []);

  useEffect(() => {
    if (!platformOptions.embed && !platformOptions.requestId) return;
    postParentMessage("ai-engine:ready", {
      requestId: platformOptions.requestId,
      sceneId: selectedSceneId,
    });
  }, [platformOptions.embed, platformOptions.requestId, selectedSceneId]);

  useEffect(() => {
    function handleParentMessage(event: MessageEvent) {
      const message = event.data;
      if (!message || typeof message !== "object" || message.type !== "ai-engine:start") return;

      const requestId = typeof message.requestId === "string" && /^[a-zA-Z0-9_-]{1,100}$/.test(message.requestId)
        ? message.requestId
        : platformOptionsRef.current.requestId;
      const nextOptions = {
        ...platformOptionsRef.current,
        requestId,
      };
      if (!canStartPlatformSession(nextOptions)) {
        postParentMessage("ai-engine:error", { message: "缺少 requestId，无法开始访谈。" });
        return;
      }
      platformOptionsRef.current = nextOptions;
      setPlatformOptions(nextOptions);
      void connectRef.current();
    }

    window.addEventListener("message", handleParentMessage);
    return () => window.removeEventListener("message", handleParentMessage);
  }, []);

  useEffect(() => {
    statusRef.current = status;
    if (status !== "connected") {
      if (status === "idle") setElapsedSeconds(0);
      return undefined;
    }

    const timer = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [status]);

  useEffect(() => {
    if (config.mode === "sc2" && config.enableMusic) {
      updateConfig((current) => ({ ...current, enableMusic: false }));
    }
  }, [config.mode, config.enableMusic]);

  useEffect(() => {
    let cancelled = false;

    async function loadRuntime() {
      try {
        const redirectPath = getSceneListRedirectPath(window.location.pathname);
        if (redirectPath) {
          window.history.replaceState(null, "", `${redirectPath}${window.location.search}`);
        }
        const routePathname = redirectPath ?? window.location.pathname;
        const routeIsSceneList = isSceneListRoute(routePathname);
        setSceneListOpen(routeIsSceneList);

        const scenes = await fetchRuntimeScenes();
        if (cancelled) return;

        const nextScenes = scenes.length ? scenes : sceneTemplates;

        setRuntimeScenes(nextScenes);
        setRuntimeError(null);

        const routeMatch = routeIsSceneList
          ? null
          : resolveSceneRoute(routePathname, window.location.search, nextScenes);
        const nextScene = routeMatch?.scene ?? nextScenes[0] ?? sceneTemplates[0];
        const nextPlatformOptions = routeMatch?.platformOptions ?? DEFAULT_PLATFORM_ROUTE_OPTIONS;
        setSelectedSceneId(nextScene.id);
        setPlatformOptions(nextPlatformOptions);
        platformOptionsRef.current = nextPlatformOptions;
        setShowTranscript(nextPlatformOptions.showTranscript);
        showTranscriptRef.current = nextPlatformOptions.showTranscript;
        if (nextPlatformOptions.embed) setSceneManagementOpen(false);
        setConfig(nextScene.config);
        setConfigDirty(false);
        setConfigSaveError(null);
        setAssistantTitle(nextScene.title);
        setAssistantLine(nextScene.config.openingLine || nextScene.subtitle);

        if (routeMatch && routeMatch.canonicalPath !== routePathname) {
          window.history.replaceState(null, "", `${routeMatch.canonicalPath}${window.location.search}`);
        } else if (!routeMatch && !routeIsSceneList) {
          window.history.replaceState(null, "", buildScenePath(nextScene));
        }
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "无法读取后端场景配置，已使用本地兜底数据。";
        setRuntimeError(message);
      }
    }

    void loadRuntime();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    memoryCardRef.current = memoryCard;
  }, [memoryCard]);

  useEffect(() => {
    memoryAutoCompressRef.current = memoryAutoCompress;
  }, [memoryAutoCompress]);

  useEffect(() => {
    memoryMaxCharsRef.current = memoryMaxChars;
  }, [memoryMaxChars]);

  useEffect(() => {
    bargeInEnabledRef.current = config.enableBargeIn;
  }, [config.enableBargeIn]);

  useEffect(() => {
    selectedSceneIdRef.current = selectedSceneId;
  }, [selectedSceneId]);

  const model = getModel(config);
  const speaker = getSpeaker(config);
  const selectedVoice = getVoiceOption(config);
  const voiceLabel = getVoiceLabel(config);
  const modeVoiceOptions = getModeVoiceOptions(config.mode);
  const selectedScene = useMemo(
    () => runtimeScenes.find((scene) => scene.id === selectedSceneId) ?? runtimeScenes[0] ?? sceneTemplates[0],
    [runtimeScenes, selectedSceneId],
  );
  const availableScenes = runtimeScenes.length ? runtimeScenes : sceneTemplates;
  const avatarVideoUrl = selectedVoice?.avatarVideoUrl ?? getLocalAvatarVideoUrl("generated/o2-vivi.mp4");
  const avatarVideoKey = `${speaker}:${avatarVideoUrl}`;

  const statusText = useMemo(() => {
    if (status === "connecting") return "正在建立实时通话";
    if (status === "connected") return "已连接豆包 Realtime";
    if (status === "ending") return "正在结束会话";
    return "准备开始语音对话";
  }, [connectionMode, status]);

  const elapsedText = useMemo(() => {
    const minutes = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
    const seconds = String(elapsedSeconds % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
  }, [elapsedSeconds]);

  const isInCall = status !== "idle";
  const conversationEvents = useMemo(() => {
    const visibleEvents = events.filter((event) => event.type !== "system");
    const historyEvents = visibleEvents[0]?.type === "asr" ? visibleEvents.slice(1) : visibleEvents;
    return historyEvents.slice().reverse();
  }, [events]);
  const latestSystemEvent = useMemo(
    () => events.find((event) => event.type === "system" && isVisibleSystemEvent(event)),
    [events],
  );
  const latestVoiceEvent = useMemo(() => events.find((event) => event.type !== "system"), [events]);
  const transcriptCue = latestVoiceEvent?.type === "asr" ? formatVoiceEventText(latestVoiceEvent.text) : "说吧，我在听。";
  const stageClassName = !isInCall ? "stage" : showTranscript ? "stage call-stage transcript-stage" : "stage call-stage";
  const memoryPreviewItems = useMemo(() => getMemoryCardPreviewItems(memoryCard), [memoryCard]);
  const memoryHasContent = hasMemoryCardContent(memoryCard);
  const memoryInjected = memoryEnabled && memoryHasContent;
  const memoryStatusText = useMemo(() => {
    if (memoryStatus === "loading") return "读取中";
    if (memoryStatus === "compressing") return "压缩中";
    if (memoryStatus === "saved") return "已保存";
    if (memoryStatus === "clearing") return "清空中";
    if (memoryStatus === "error") return "异常";
    if (memoryStatus === "empty") return "暂无记忆";
    if (memoryInjected) return "下次会注入";
    return "未注入";
  }, [memoryInjected, memoryStatus]);
  const selectedSceneIsPodcast = isPodcastScene(selectedScene);
  const scenePickerVisible = shouldShowScenePicker(platformOptions);
  const sessionStartAllowed = canStartPlatformSession(platformOptions);
  const manualStartVisible = shouldShowManualStartButton(platformOptions);
  const textComposerVisible = shouldShowTextComposer(platformOptions);
  const podcastHostA = selectedScene.config.podcastHostA || selectedScene.podcastProfile?.hostA || DEFAULT_PODCAST_PROFILE.hostA;
  const podcastHostB = selectedScene.config.podcastHostB || selectedScene.podcastProfile?.hostB || DEFAULT_PODCAST_PROFILE.hostB;
  const podcastStyle = selectedScene.config.podcastStyle || selectedScene.podcastProfile?.style || DEFAULT_PODCAST_PROFILE.style;

  useEffect(() => {
    if (availableScenes.some((scene) => scene.id === selectedScene.id)) return;

    const nextScene = availableScenes[0];
    setSelectedSceneId(nextScene.id);
    setConfig(nextScene.config);
    setConfigDirty(false);
    setConfigSaveError(null);
    setAssistantTitle(nextScene.title);
    setAssistantLine(nextScene.config.openingLine || nextScene.subtitle);
    setApiPreview(null);
    setLastError(null);
    setCallReport(null);
  }, [availableScenes, selectedScene.id]);

  async function loadCallLogs(sceneId = selectedScene.id) {
    setCallLogStatus("loading");
    setCallLogError(null);
    try {
      const logs = await fetchRuntimeCallLogs(undefined, sceneId, 10);
      if (sceneId === selectedSceneIdRef.current) {
        setCallLogs(logs);
        setCallLogStatus("idle");
      }
      return logs;
    } catch (error) {
      setCallLogs([]);
      setCallLogStatus("error");
      setCallLogError(error instanceof Error ? error.message : "无法读取访谈日志。");
      return [];
    }
  }

  async function loadMemoryCard() {
    setMemoryStatus("empty");
    setMemoryError(null);
    setMemoryWarnings([]);
    setMemoryCard(null);
    return null;
  }

  async function clearMemoryCard() {
    setMemoryStatus("empty");
    setMemoryError(null);
    setMemoryWarnings([]);
    setMemoryCard(null);
  }

  async function compressCallReport(_report: CallReport, _sceneId: SceneTemplate["id"]) {
    if (!memoryAutoCompressRef.current) return;
    setMemoryStatus("empty");
  }

  function selectScene(scene: SceneTemplate) {
    if (isInCall) return;
    setSceneListOpen(false);
    setSelectedSceneId(scene.id);
    setConfig(scene.config);
    window.history.pushState(null, "", `${buildScenePath(scene)}${window.location.search}`);
    setConfigDirty(false);
    setConfigSaveError(null);
    setApiPreview(null);
    setLastError(null);
    setCallReport(null);
    setAssistantTitle(scene.title);
    setAssistantLine(scene.config.openingLine || scene.subtitle);
  }

  function finalizeCallReport() {
    if (
      reportFinalizedRef.current
      || !sessionConnectedRef.current
      || sessionStartedAtRef.current === null
      || !metricsRef.current
    ) {
      return;
    }

    reportFinalizedRef.current = true;
    const scene = activeSceneRef.current;
    const report = buildCallReport({
      events: transcriptEventsRef.current,
      metrics: metricsRef.current,
      scene,
      startedAtLabel: sessionStartedAtLabelRef.current,
      startedAtMs: sessionStartedAtRef.current,
      tokens: tokensRef.current,
      userName: "场景访客",
      userSegment: "scene-route",
    });

    setCallReport(report);
    if (platformOptionsRef.current.saveCallLog) {
      void persistCallLog(report, scene.id);
    }
    void compressCallReport(report, scene.id);
    postParentMessage("ai-engine:finished", {
      requestId: platformOptionsRef.current.requestId,
      sessionId: platformSessionIdRef.current,
    });
  }

  async function persistCallLog(report: CallReport, sceneId: SceneTemplate["id"]) {
    setCallLogStatus("saving");
    setCallLogError(null);
    try {
      const log = await saveRuntimeCallLog(EMBEDDED_SCENE_USER_ID, sceneId, report, {
        requestId: platformOptionsRef.current.requestId,
        sessionId: platformSessionIdRef.current ?? undefined,
      });
      if (sceneId === selectedSceneIdRef.current) {
        setCallLogs((current) => [log, ...current.filter((item) => item.id !== log.id)].slice(0, 10));
      }
      setCallLogStatus("saved");
    } catch (error) {
      setCallLogStatus("error");
      setCallLogError(error instanceof Error ? error.message : "无法保存访谈日志。");
    }
  }

  function recordEvent(event: VoiceEvent) {
    const forceNewTurn = event.type === "assistant" && forceNextAssistantTurnRef.current;
    transcriptEventsRef.current = appendTranscriptEvent(transcriptEventsRef.current, event, { forceNewTurn });
    if (forceNewTurn) {
      forceNextAssistantTurnRef.current = false;
    }
    if (!showTranscriptRef.current) return;
    setEvents((current) => {
      const nextEvents = appendDisplayEvent(current, event, { forceNewTurn });
      eventsRef.current = nextEvents;
      return nextEvents;
    });
  }

  function makeSystemEvent(text: string): VoiceEvent {
    return {
      id: createClientId(),
      type: "system",
      text,
      at: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
    };
  }

  function resetBargeInTracking() {
    bargeInRef.current = resetBargeInSnapshot();
    localBargeInCandidateAtRef.current = null;
  }

  function resetAssistantOutputTracking() {
    activeAssistantOutputIdRef.current = null;
    activeAssistantOutputIdsRef.current.clear();
    discardedAssistantOutputIdsRef.current.clear();
  }

  function discardActiveAssistantOutputs() {
    if (activeAssistantOutputIdRef.current) {
      discardedAssistantOutputIdsRef.current.add(activeAssistantOutputIdRef.current);
    }
    activeAssistantOutputIdsRef.current.forEach((outputId) => {
      discardedAssistantOutputIdsRef.current.add(outputId);
    });
  }

  function updateConfig(nextConfig: React.SetStateAction<RealtimeConfig>) {
    setConfig((current) => {
      const resolved = typeof nextConfig === "function"
        ? (nextConfig as (value: RealtimeConfig) => RealtimeConfig)(current)
        : nextConfig;
      return resolved;
    });
    setConfigDirty(true);
    setConfigSaveError(null);
  }

  function interruptPlaybackInternal(recordSystemEvent: boolean, notifyUpstream: boolean) {
    if (statusRef.current === "idle") return;
    const targetOutputId = activeAssistantOutputIdRef.current;
    discardActiveAssistantOutputs();
    forceNextAssistantTurnRef.current = true;
    stopPlayback();
    localBargeInCandidateAtRef.current = notifyUpstream ? null : performance.now();
    bargeInRef.current = markBargeInInterrupted(bargeInRef.current);
    playbackMutedRef.current = false;
    if (!recordSystemEvent) {
      scheduleAutoInterruptRelease();
    }
    if (recordSystemEvent) {
      recordEvent(makeSystemEvent("我停下了，你继续说。"));
    }
    if (notifyUpstream && socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "interrupt", targetOutputId }));
    }
  }

  function interruptPlayback() {
    interruptPlaybackInternal(true, true);
  }

  function autoInterruptPlayback(notifyUpstream: boolean) {
    interruptPlaybackInternal(false, notifyUpstream);
  }

  async function saveCurrentSceneConfig() {
    if (configSaving) return selectedScene;

    setConfigSaving(true);
    setConfigSaveError(null);
    try {
      const savedScene = await saveRuntimeSceneConfig(selectedScene.id, config);
      setRuntimeScenes((current) => current.map((scene) => scene.id === savedScene.id ? savedScene : scene));
      setSelectedSceneId(savedScene.id);
      setConfig(savedScene.config);
      setConfigDirty(false);
      setAssistantTitle(savedScene.title);
      setAssistantLine(savedScene.config.openingLine || savedScene.subtitle);
      return savedScene;
    } catch (error) {
      const message = error instanceof Error ? error.message : "无法保存场景配置。";
      setConfigSaveError(message);
      throw error;
    } finally {
      setConfigSaving(false);
    }
  }

  async function createAdminScene(input: CreateSceneInput) {
    const result = await createRuntimeScene("", input);
    setRuntimeScenes((current) => [...current, result.scene]);
    setSceneListOpen(false);
    setSelectedSceneId(result.scene.id);
    setConfig(result.scene.config);
    window.history.pushState(null, "", buildScenePath(result.scene));
    setConfigDirty(false);
    setConfigSaveError(null);
    setApiPreview(null);
    setLastError(null);
    setCallReport(null);
    setAssistantTitle(result.scene.title);
    setAssistantLine(result.scene.config.openingLine || result.scene.subtitle);
  }

  async function updateAdminScene(sceneId: string, input: CreateSceneInput) {
    const scene = await updateRuntimeScene("", sceneId, input);
    setRuntimeScenes((current) => current.map((item) => item.id === scene.id ? scene : item));
    if (selectedSceneId === scene.id) {
      setConfig(scene.config);
      setConfigDirty(false);
      setConfigSaveError(null);
      setAssistantTitle(scene.title);
      setAssistantLine(scene.config.openingLine || scene.subtitle);
      const path = buildScenePath(scene);
      if (window.location.pathname !== path) {
        window.history.replaceState(null, "", path);
      }
    }
  }

  function openApplicationForm(scene: SceneTemplate) {
    setApplicationForm(createSceneApplicationForm(scene, createClientId()));
  }

  function openApplicationUrl(form: SceneApplicationForm) {
    window.open(buildSceneApplicationUrl(form), "_blank", "noopener,noreferrer");
    setApplicationForm(null);
  }

  function updateApplicationForm(patch: Partial<SceneApplicationParams>) {
    setApplicationForm((current) => current ? { ...current, ...patch } : current);
  }

  async function loadPayloadPreview(nextConfig = config) {
    const response = await fetch(`${getBackendBaseUrl()}/payload-preview`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ config: nextConfig }),
    });
    if (!response.ok) {
      throw new Error("无法生成 API 调用参数。");
    }
    const preview = (await response.json()) as PayloadPreview;
    setApiPreview(preview);
    return preview;
  }

  async function openApiDrawer() {
    setApiDrawerOpen(true);
    try {
      await loadPayloadPreview();
    } catch (error) {
      setApiPreview({
        payload: { error: error instanceof Error ? error.message : "无法生成 API 调用参数。" },
      });
    }
  }

  async function previewVoice() {
    if (!speaker || voicePreviewing) return;

    setVoicePreviewing(true);
    setLastError(null);
    stopPlayback();

    const playbackReady = await ensurePlaybackReady("voice-preview");
    if (!playbackReady) {
      setVoicePreviewing(false);
      setLastError("当前浏览器不支持音频播放，无法试听音色。");
      return;
    }

    try {
      const response = await fetch(`${getBackendBaseUrl()}/voice-preview`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          config,
          text: selectedVoice?.previewText ?? `你好，我是 ${voiceLabel}。`,
        }),
      });
      const preview = (await response.json()) as VoicePreviewResponse;
      if (!response.ok || !preview.data) {
        throw new Error(preview.error || "无法生成音色试听。");
      }
      queuePcmAudio(preview.data);
    } catch (error) {
      stopPlayback();
      setLastError(error instanceof Error ? error.message : "无法生成音色试听。");
    } finally {
      setVoicePreviewing(false);
    }
  }

  function handleServerMessage(message: MessageEvent<string>) {
    const data = JSON.parse(message.data) as ServerMessage;
    if (data.type === "status") {
      setStatus(data.status);
      if (data.mode) setConnectionMode(data.mode);
      if (data.sessionId) {
        platformSessionIdRef.current = data.sessionId;
        postParentMessage("ai-engine:started", {
          requestId: data.requestId ?? platformOptionsRef.current.requestId,
          sessionId: data.sessionId,
        });
      }
      audioUploadReadyRef.current = data.status === "connected";
      if (data.status === "connected" && metricsRef.current) {
        metricsRef.current.connectedAt ??= performance.now();
        sessionConnectedRef.current = true;
      }
      if (data.status === "idle") {
        finalizeCallReport();
        playbackMutedRef.current = true;
        stopSilenceKeepAlive();
        stopMicrophone();
        stopPlayback({ closeContext: true });
        resetAssistantOutputTracking();
      }
      return;
    }

    if (data.type === "payload") {
      setApiPreview({
        payload: data.payload,
        warnings: data.warnings,
        mode: data.mode,
      });
      return;
    }

    if (data.type === "usage") {
      setTokens(data.tokens);
      tokensRef.current = data.tokens;
      return;
    }

    if (data.type === "interrupt_ack") {
      if (data.targetOutputId) {
        discardedAssistantOutputIdsRef.current.add(data.targetOutputId);
      }
      return;
    }

    if (data.type === "audio") {
      if (playbackMutedRef.current) return;
      if (data.outputId && discardedAssistantOutputIdsRef.current.has(data.outputId)) return;
      if (metricsRef.current) {
        metricsRef.current.firstAudioAt ??= performance.now();
      }
      assistantAudioActiveUntilRef.current = performance.now() + ASSISTANT_AUDIO_ACTIVE_GRACE_MS;
      queuePcmAudio(data.data, data.outputId);
      return;
    }

    if (data.type === "event") {
      if (
        data.event.type === "assistant" &&
        data.event.outputId &&
        discardedAssistantOutputIdsRef.current.has(data.event.outputId)
      ) {
        return;
      }
      if (metricsRef.current) {
        if (data.event.type === "asr") metricsRef.current.firstAsrAt ??= performance.now();
        if (data.event.type === "assistant") metricsRef.current.firstAssistantAt ??= performance.now();
      }
      recordEvent(data.event);
      if (data.event.type === "assistant") {
        localBargeInCandidateAtRef.current = null;
        if (data.event.outputId) {
          activeAssistantOutputIdRef.current = data.event.outputId;
          activeAssistantOutputIdsRef.current.add(data.event.outputId);
        }
        clearAutoInterruptReleaseTimer();
        bargeInRef.current = markBargeInRecovering(bargeInRef.current);
        const assistantText = getAssistantEventText(data.event.text);
        latestAssistantSpeechRef.current = assistantText;
        setAssistantTitle("我在听。");
        setAssistantLine(assistantText);
      }
      if (data.event.type === "asr") {
        const asrText = getAsrEventText(data.event.text);
        const nowMs = performance.now();
        const recentSpeechCandidateAt =
          bargeInRef.current.recentSpeechCandidateAt ?? localBargeInCandidateAtRef.current;
        const hasRecentSpeechCandidate =
          recentSpeechCandidateAt !== null
          && nowMs - recentSpeechCandidateAt <= defaultBargeInConfig.candidateWindowMs;
        const shouldInterrupt =
          bargeInEnabledRef.current
          && (isAssistantOutputActive(nowMs) || hasRecentSpeechCandidate)
          && shouldConfirmBargeInFromAsr(
            asrText,
            latestAssistantSpeechRef.current,
            recentSpeechCandidateAt,
            nowMs,
          );
        if (shouldInterrupt) {
          autoInterruptPlayback(true);
        } else {
          localBargeInCandidateAtRef.current = null;
        }
        setAssistantTitle("听到了。");
        setAssistantLine(asrText);
      }
      return;
    }

    if (data.type === "error") {
      if (data.payload) setApiPreview({ payload: data.payload, warnings: data.warnings });
      if (metricsRef.current) metricsRef.current.errors.push(data.message);
      audioUploadReadyRef.current = false;
      playbackMutedRef.current = true;
      clearAutoInterruptReleaseTimer();
      stopMicrophone();
      stopPlayback({ closeContext: true });
      socketRef.current?.close();
      setLastError(data.message);
      recordEvent(makeSystemEvent(data.message));
      postParentMessage("ai-engine:error", {
        message: data.message,
        requestId: platformOptionsRef.current.requestId,
        sessionId: platformSessionIdRef.current,
      });
      finalizeCallReport();
      setStatus("idle");
    }
  }

  async function connect() {
    if (status !== "idle") return;
    if (!canStartPlatformSession(platformOptionsRef.current)) {
      setLastError("请先创建访谈请求，再开始对话。");
      return;
    }

    stopPlayback();
    const playbackReady = await ensurePlaybackReady("connect");
    if (!playbackReady) {
      setLastError("当前浏览器不支持音频播放，无法开始真实语音通话。");
      return;
    }

    let sessionScene = selectedScene;
    if (configDirty) {
      try {
        sessionScene = await saveCurrentSceneConfig();
      } catch {
        setLastError("场景配置保存失败，未开始通话。");
        return;
      }
    }

    setStatus("connecting");
    setEvents([]);
    eventsRef.current = [];
    transcriptEventsRef.current = [];
    setLastError(null);
    setCallReport(null);
    const initialAssistantLine = config.openingLine || "你好呀，今天过得怎么样";
    setAssistantTitle("你好。");
    setAssistantLine(initialAssistantLine);
    setElapsedSeconds(0);
    setTokens(null);
    tokensRef.current = null;
    setMicrophoneEnabled(true);
    microphoneEnabledRef.current = true;
    playbackMutedRef.current = false;
    forceNextAssistantTurnRef.current = false;
    clearAutoInterruptReleaseTimer();
    resetBargeInTracking();
    assistantAudioActiveUntilRef.current = 0;
    latestAssistantSpeechRef.current = initialAssistantLine;
    resetAssistantOutputTracking();
    setConnectionMode(null);
    activeSceneRef.current = sessionScene;
    platformSessionIdRef.current = null;
    sessionStartedAtRef.current = Date.now();
    sessionStartedAtLabelRef.current = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    metricsRef.current = {
      connectStartedAt: performance.now(),
      errors: [],
    };
    reportFinalizedRef.current = false;
    sessionConnectedRef.current = false;

    const ws = new WebSocket(getBackendWsUrl("/realtime"));
    ws.binaryType = "arraybuffer";
    socketRef.current = ws;

    ws.onopen = async () => {
      if (metricsRef.current) metricsRef.current.wsOpenedAt ??= performance.now();
      const micReady = await startMicrophone(ws);
      if (socketRef.current !== ws || ws.readyState !== WebSocket.OPEN) {
        stopMicrophone();
        ws.close();
        setStatus("idle");
        return;
      }
      if (!micReady) {
        microphoneEnabledRef.current = false;
        audioUploadReadyRef.current = false;
        setMicrophoneEnabled(false);
        setAssistantTitle("麦克风未开启。");
        setAssistantLine("仍可使用文字输入；点击底部麦克风按钮可重新开启语音输入。");
        startSilenceKeepAlive(ws);
      }

      ws.send(
        JSON.stringify({
          type: "start",
          payload: {
            sceneId: sessionScene.id,
            memoryEnabled,
            recordAudio: platformOptionsRef.current.recordAudio,
            requestId: platformOptionsRef.current.requestId,
          },
        }),
      );
    };

    ws.onmessage = (message) => {
      if (socketRef.current !== ws) return;
      handleServerMessage(message);
    };

    ws.onclose = () => {
      if (socketRef.current !== ws) return;
      socketRef.current = null;
      audioUploadReadyRef.current = false;
      playbackMutedRef.current = true;
      clearAutoInterruptReleaseTimer();
      finalizeCallReport();
      stopSilenceKeepAlive();
      stopMicrophone();
      stopPlayback({ closeContext: true });
      setStatus("idle");
    };

    ws.onerror = () => {
      if (socketRef.current !== ws) return;
      if (metricsRef.current) metricsRef.current.errors.push("本地实时通话服务未连接，请确认后端服务已启动。");
      setStatus("idle");
      audioUploadReadyRef.current = false;
      playbackMutedRef.current = true;
      clearAutoInterruptReleaseTimer();
      stopSilenceKeepAlive();
      stopMicrophone();
      stopPlayback({ closeContext: true });
      recordEvent(makeSystemEvent("本地实时通话服务未连接，请确认后端服务已启动。"));
      setLastError("本地实时通话服务未连接，请确认后端服务已启动。");
      finalizeCallReport();
    };
  }

  connectRef.current = connect;

  function endCall() {
    if (status === "idle") return;

    const ws = socketRef.current;
    socketRef.current = null;
    audioUploadReadyRef.current = false;
    playbackMutedRef.current = true;
    clearAutoInterruptReleaseTimer();
    resetBargeInTracking();
    assistantAudioActiveUntilRef.current = 0;
    resetAssistantOutputTracking();
    stopSilenceKeepAlive();
    stopMicrophone();
    stopPlayback({ closeContext: true });
    finalizeCallReport();
    setStatus("idle");

    if (!ws) return;
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "finish" }));
    }
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  }

  function toggleRecording() {
    setShowTranscript((enabled) => {
      const nextEnabled = !enabled;
      showTranscriptRef.current = nextEnabled;
      return nextEnabled;
    });
  }

  async function toggleMicrophone() {
    if (microphoneEnabledRef.current) {
      microphoneEnabledRef.current = false;
      playbackMutedRef.current = true;
      clearAutoInterruptReleaseTimer();
      resetBargeInTracking();
      assistantAudioActiveUntilRef.current = 0;
      resetAssistantOutputTracking();
      setMicrophoneEnabled(false);
      stopMicrophone();
      stopPlayback();
      if (socketRef.current) startSilenceKeepAlive(socketRef.current);
      recordEvent(makeSystemEvent("已静音，当前播报已停止。"));
      return;
    }

    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || status === "idle" || status === "ending") {
      return;
    }

    microphoneEnabledRef.current = true;
    playbackMutedRef.current = false;
    stopSilenceKeepAlive();
    const micReady = await startMicrophone(ws);
    if (!micReady) {
      microphoneEnabledRef.current = false;
      playbackMutedRef.current = true;
      clearAutoInterruptReleaseTimer();
      setMicrophoneEnabled(false);
      startSilenceKeepAlive(ws);
      return;
    }

    audioUploadReadyRef.current = status === "connected";
    setMicrophoneEnabled(true);
    recordEvent(makeSystemEvent("已恢复语音输入和播报。"));
  }

  async function startMicrophone(ws: WebSocket) {
    if (!navigator.mediaDevices?.getUserMedia) {
      const text = "当前浏览器不支持麦克风采集，无法开始真实语音通话。";
      recordEvent(makeSystemEvent(text));
      setLastError(text);
      return false;
    }

    try {
      const nativePermissionGranted = await requestAndroidMicrophonePermission();
      if (!nativePermissionGranted) {
        const text = "系统麦克风权限未开启，无法开始真实语音通话。请在应用权限里允许 AI Engine 使用麦克风。";
        recordEvent(makeSystemEvent(text));
        setLastError(text);
        return false;
      }

      stopMicrophone();
      const stream = await getMicrophoneStream();
      const AudioContextClass =
        window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextClass) throw new Error("AudioContext is unavailable.");

      const audioContext = new AudioContextClass();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(2048, 1, 1);

      processor.onaudioprocess = (event) => {
        if (!audioUploadReadyRef.current || !microphoneEnabledRef.current || ws.readyState !== WebSocket.OPEN) return;
        const input = event.inputBuffer.getChannelData(0);
        const playbackActive = bargeInEnabledRef.current && isPlaybackActive();
        bargeInRef.current = observeBargeInAudio(input, playbackActive, bargeInRef.current, performance.now());
        const pcm = encodePcm16(resampleTo16k(input, audioContext.sampleRate));
        if (pcm.byteLength > 0) ws.send(pcm);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      micStreamRef.current = stream;
      audioContextRef.current = audioContext;
      audioProcessorRef.current = processor;
      micSourceRef.current = source;
      return true;
    } catch (error) {
      const text = getMicrophoneFailureText(error);
      recordEvent(makeSystemEvent(text));
      recordEvent(makeSystemEvent(`麦克风错误详情：${getMicrophoneFailureDetail(error)}`));
      recordEvent(makeSystemEvent(`麦克风设备详情：${await getAudioInputSummary()}`));
      setLastError(text);
      return false;
    }
  }

  async function getMicrophoneStream() {
    try {
      return await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch (error) {
      if (!isRecoverableMicrophoneStartError(error)) {
        throw error;
      }

      await sleep(MICROPHONE_RETRY_DELAY_MS);
      recordEvent(makeSystemEvent("麦克风增强参数启动失败，已切换为兼容模式重试。"));
      recordEvent(makeSystemEvent(`麦克风设备详情：${await getAudioInputSummary()}`));
      return navigator.mediaDevices.getUserMedia({ audio: true });
    }
  }

  function stopMicrophone() {
    audioProcessorRef.current?.disconnect();
    micSourceRef.current?.disconnect();
    micStreamRef.current?.getTracks().forEach((track) => track.stop());
    void audioContextRef.current?.close().catch(() => undefined);

    audioProcessorRef.current = null;
    micSourceRef.current = null;
    micStreamRef.current = null;
    audioContextRef.current = null;
    resetBargeInTracking();
  }

  function startSilenceKeepAlive(ws: WebSocket) {
    if (silenceTimerRef.current !== null) return;

    const silenceFrame = new ArrayBuffer(640);
    silenceTimerRef.current = window.setInterval(() => {
      if (
        ws.readyState === WebSocket.OPEN &&
        audioUploadReadyRef.current &&
        !microphoneEnabledRef.current
      ) {
        ws.send(silenceFrame.slice(0));
      }
    }, 200);
  }

  function stopSilenceKeepAlive() {
    if (silenceTimerRef.current === null) return;
    window.clearInterval(silenceTimerRef.current);
    silenceTimerRef.current = null;
  }

  function scheduleAutoInterruptRelease() {
    clearAutoInterruptReleaseTimer();
    autoInterruptReleaseTimerRef.current = window.setTimeout(() => {
      resetBargeInTracking();
      autoInterruptReleaseTimerRef.current = null;
    }, AUTO_INTERRUPT_RELEASE_MS);
  }

  function clearAutoInterruptReleaseTimer() {
    if (autoInterruptReleaseTimerRef.current === null) return;
    window.clearTimeout(autoInterruptReleaseTimerRef.current);
    autoInterruptReleaseTimerRef.current = null;
  }

  function isPlaybackActive() {
    return playbackSourcesRef.current.size > 0 && !playbackMutedRef.current;
  }

  function isAssistantOutputActive(nowMs = performance.now()) {
    return (
      isPlaybackActive()
      || (!playbackMutedRef.current && nowMs <= assistantAudioActiveUntilRef.current)
    );
  }

  function logPlayback(kind: string, details: Record<string, unknown> = {}) {
    try {
      console.info(`${PLAYBACK_LOG_PREFIX} ${JSON.stringify({ kind, ...details })}`);
    } catch {
      console.info(`${PLAYBACK_LOG_PREFIX} ${kind}`);
    }
  }

  function getPlaybackContext() {
    const AudioContextClass =
      window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) {
      logPlayback("context_unavailable");
      return null;
    }

    if (!playbackContextRef.current || playbackContextRef.current.state === "closed") {
      playbackContextRef.current = createPlaybackContext(AudioContextClass);
      nextPlaybackTimeRef.current = playbackContextRef.current.currentTime + PLAYBACK_START_LEAD_SECONDS;
      logPlayback("context_created", getPlaybackContextLog(playbackContextRef.current));
    }

    return playbackContextRef.current;
  }

  function createPlaybackContext(AudioContextClass: typeof AudioContext) {
    try {
      return new AudioContextClass({ sampleRate: 24000 });
    } catch {
      return new AudioContextClass();
    }
  }

  function getPlaybackContextLog(playbackContext: AudioContext) {
    const latencyContext = playbackContext as AudioContext & { outputLatency?: number };
    return {
      baseLatency: playbackContext.baseLatency,
      currentTime: Number(playbackContext.currentTime.toFixed(3)),
      outputLatency: latencyContext.outputLatency,
      sampleRate: playbackContext.sampleRate,
      state: playbackContext.state,
    };
  }

  async function ensurePlaybackReady(reason: string) {
    const playbackContext = getPlaybackContext();
    if (!playbackContext) return false;

    logPlayback("ready_start", { reason, ...getPlaybackContextLog(playbackContext) });

    try {
      if (playbackContext.state === "suspended") {
        await playbackContext.resume();
        logPlayback("resume_done", { reason, ...getPlaybackContextLog(playbackContext) });
      }
      primePlaybackOutput(playbackContext, reason);
      if (metricsRef.current) {
        metricsRef.current.playbackReadyAt ??= performance.now();
      }
      logPlayback("ready_done", { reason, ...getPlaybackContextLog(playbackContext) });
      return playbackContext.state !== "closed";
    } catch (error) {
      const message = error instanceof Error ? error.message : "unknown playback resume error";
      if (metricsRef.current) {
        metricsRef.current.errors.push(`音频播放初始化失败：${message}`);
      }
      logPlayback("ready_failed", { message, reason, ...getPlaybackContextLog(playbackContext) });
      return false;
    }
  }

  function primePlaybackOutput(playbackContext: AudioContext, reason: string) {
    const sampleCount = Math.max(1, Math.round(playbackContext.sampleRate * PLAYBACK_UNLOCK_SECONDS));
    const buffer = playbackContext.createBuffer(1, sampleCount, playbackContext.sampleRate);
    const source = playbackContext.createBufferSource();
    const gain = playbackContext.createGain();
    gain.gain.value = 0;
    source.buffer = buffer;
    source.connect(gain);
    gain.connect(playbackContext.destination);
    source.onended = () => {
      try {
        source.disconnect();
        gain.disconnect();
      } catch {
        // The context may already be closed during call teardown.
      }
      logPlayback("unlock_ended", { reason });
    };
    source.start();
    logPlayback("unlock_started", { durationMs: Math.round(buffer.duration * 1000), reason });
  }

  function queuePcmAudio(base64: string, outputId?: string) {
    const chunk = createPlaybackChunk(base64, outputId);
    if (!chunk) return;

    if (!outputId || prebufferedOutputIdsRef.current.has(outputId)) {
      schedulePlaybackChunk(chunk);
      return;
    }

    const pendingChunks = pendingPlaybackChunksRef.current.get(outputId) ?? [];
    pendingChunks.push(chunk);
    pendingPlaybackChunksRef.current.set(outputId, pendingChunks);

    const bufferedSeconds = pendingChunks.reduce((total, item) => total + item.sampleCount, 0) / 24000;
    const oldestChunk = pendingChunks[0] ?? chunk;
    logPlayback("chunk_buffered", {
      bufferedMs: Math.round(bufferedSeconds * 1000),
      byteLength: chunk.byteLength,
      firstChunkAgeMs: Math.round(performance.now() - oldestChunk.receivedAtMs),
      interArrivalMs: chunk.interArrivalMs,
      outputId,
      pendingChunks: pendingChunks.length,
      sequence: chunk.sequence,
    });

    if (!playbackPrebufferTimersRef.current.has(outputId)) {
      const timer = window.setTimeout(() => {
        flushBufferedPlayback(outputId, "timer");
      }, PLAYBACK_PREROLL_SECONDS * 1000);
      playbackPrebufferTimersRef.current.set(outputId, timer);
    }

    if (bufferedSeconds >= PLAYBACK_PREROLL_SECONDS) {
      flushBufferedPlayback(outputId, "duration");
    }
  }

  function createPlaybackChunk(base64: string, outputId?: string): PendingPlaybackChunk | null {
    const receivedAtMs = performance.now();
    let binary = "";
    try {
      binary = atob(base64);
    } catch (error) {
      const message = error instanceof Error ? error.message : "invalid base64 audio";
      if (metricsRef.current) {
        metricsRef.current.errors.push(`音频解码失败：${message}`);
      }
      logPlayback("decode_failed", { message, outputId });
      return null;
    }

    const sampleCount = Math.floor(binary.length / 2);
    if (!sampleCount) {
      logPlayback("empty_chunk", { byteLength: binary.length, outputId });
      return null;
    }

    playbackChunkSequenceRef.current += 1;
    const lastReceivedAtMs = lastPlaybackChunkReceivedAtRef.current;
    lastPlaybackChunkReceivedAtRef.current = receivedAtMs;
    return {
      binary,
      byteLength: binary.length,
      interArrivalMs: lastReceivedAtMs === null ? null : Math.round(receivedAtMs - lastReceivedAtMs),
      outputId,
      receivedAtMs,
      sampleCount,
      sequence: playbackChunkSequenceRef.current,
    };
  }

  function flushBufferedPlayback(outputId: string, reason: string) {
    const pendingChunks = pendingPlaybackChunksRef.current.get(outputId);
    if (!pendingChunks?.length) return;

    const timer = playbackPrebufferTimersRef.current.get(outputId);
    if (timer !== undefined) {
      window.clearTimeout(timer);
      playbackPrebufferTimersRef.current.delete(outputId);
    }

    pendingPlaybackChunksRef.current.delete(outputId);
    prebufferedOutputIdsRef.current.add(outputId);

    const bufferedSeconds = pendingChunks.reduce((total, item) => total + item.sampleCount, 0) / 24000;
    const oldestChunk = pendingChunks[0];
    logPlayback("prebuffer_flush", {
      bufferedMs: Math.round(bufferedSeconds * 1000),
      chunks: pendingChunks.length,
      firstChunkAgeMs: oldestChunk ? Math.round(performance.now() - oldestChunk.receivedAtMs) : undefined,
      outputId,
      reason,
    });

    const scheduledStartedAtMs = performance.now();
    pendingChunks.forEach((chunk) => schedulePlaybackChunk(chunk));
    logPlayback("prebuffer_scheduled", {
      chunks: pendingChunks.length,
      elapsedMs: Math.round(performance.now() - scheduledStartedAtMs),
      outputId,
      reason,
    });
  }

  function schedulePlaybackChunk(chunk: PendingPlaybackChunk) {
    const playbackContext = getPlaybackContext();
    if (!playbackContext) return;

    if (playbackContext.state === "suspended") {
      void ensurePlaybackReady("schedule");
    }

    const buffer = playbackContext.createBuffer(1, chunk.sampleCount, 24000);
    const channel = buffer.getChannelData(0);
    for (let index = 0; index < chunk.sampleCount; index += 1) {
      const low = chunk.binary.charCodeAt(index * 2);
      const high = chunk.binary.charCodeAt(index * 2 + 1);
      const value = (high << 8) | low;
      const signed = value >= 0x8000 ? value - 0x10000 : value;
      channel[index] = signed / 0x8000;
    }

    const source = playbackContext.createBufferSource();
    source.buffer = buffer;
    source.connect(playbackContext.destination);

    const queueWasIdle =
      playbackSourcesRef.current.size === 0 || nextPlaybackTimeRef.current <= playbackContext.currentTime;
    const backlogBeforeMs = Math.max(0, Math.round((nextPlaybackTimeRef.current - playbackContext.currentTime) * 1000));
    const underrunBeforeMs = Math.max(0, Math.round((playbackContext.currentTime - nextPlaybackTimeRef.current) * 1000));
    if (queueWasIdle) {
      nextPlaybackTimeRef.current = playbackContext.currentTime + PLAYBACK_START_LEAD_SECONDS;
    }

    const leadSeconds = queueWasIdle ? PLAYBACK_START_LEAD_SECONDS : PLAYBACK_CONTINUATION_LEAD_SECONDS;
    const startAt = Math.max(playbackContext.currentTime + leadSeconds, nextPlaybackTimeRef.current);

    if (chunk.outputId) {
      activeAssistantOutputIdsRef.current.add(chunk.outputId);
    }
    playbackSourcesRef.current.add(source);
    source.onended = () => {
      playbackSourcesRef.current.delete(source);
      if (chunk.outputId) {
        activeAssistantOutputIdsRef.current.delete(chunk.outputId);
      }
      logPlayback("chunk_ended", {
        outputId: chunk.outputId,
        remainingSources: playbackSourcesRef.current.size,
        sequence: chunk.sequence,
      });
    };

    source.start(startAt);
    nextPlaybackTimeRef.current = startAt + buffer.duration;

    if (metricsRef.current) {
      metricsRef.current.firstPlaybackScheduledAt ??= performance.now();
    }

    logPlayback("chunk_scheduled", {
      byteLength: chunk.byteLength,
      backlogBeforeMs,
      currentTime: Number(playbackContext.currentTime.toFixed(3)),
      durationMs: Math.round(buffer.duration * 1000),
      interArrivalMs: chunk.interArrivalMs,
      leadMs: Math.round((startAt - playbackContext.currentTime) * 1000),
      outputId: chunk.outputId,
      queueWasIdle,
      receivedAgoMs: Math.round(performance.now() - chunk.receivedAtMs),
      sequence: chunk.sequence,
      startAt: Number(startAt.toFixed(3)),
      state: playbackContext.state,
      underrunBeforeMs,
    });
  }

  function stopPlayback(options: { closeContext?: boolean } = {}) {
    playbackPrebufferTimersRef.current.forEach((timer) => {
      window.clearTimeout(timer);
    });
    playbackPrebufferTimersRef.current.clear();
    pendingPlaybackChunksRef.current.clear();
    prebufferedOutputIdsRef.current.clear();
    playbackSourcesRef.current.forEach((source) => {
      source.onended = null;
      try {
        source.stop(0);
      } catch {
        // Source may not have started yet or may have already ended.
      }
    });
    playbackSourcesRef.current.clear();
    activeAssistantOutputIdsRef.current.clear();
    nextPlaybackTimeRef.current = 0;
    lastPlaybackChunkReceivedAtRef.current = null;
    if (options.closeContext) {
      void playbackContextRef.current?.close().catch(() => undefined);
      playbackContextRef.current = null;
    }
    resetBargeInTracking();
    assistantAudioActiveUntilRef.current = 0;
  }

  function submitDraft() {
    const text = draft.trim();
    if (!text || status !== "connected" || !socketRef.current) return;

    if (isAssistantOutputActive()) {
      autoInterruptPlayback(true);
    }
    recordEvent({
      id: createClientId(),
      type: "asr",
      text: `ASRResponse: ${text}`,
      at: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
    });
    setAssistantTitle("思考中。");
    setAssistantLine(text);
    socketRef.current.send(JSON.stringify({ type: "user_text", text }));
    setDraft("");
  }

  return (
    <main className="app-shell">
      <HeaderBar
        apiEnabled={!sceneListOpen}
        embedded={platformOptions.embed}
        inCall={isInCall}
        onManageScenes={() => setSceneManagementOpen((open) => !open)}
        onOpenApi={openApiDrawer}
        sceneManagementOpen={sceneManagementOpen}
        showUsage={!platformOptions.embed && !sceneListOpen}
        title={platformOptions.consoleTitle}
        tokens={tokens}
      />

      {!platformOptions.embed && sceneManagementOpen ? (
        <AdminDashboard
          onCreateScene={createAdminScene}
          onUpdateScene={updateAdminScene}
          runtimeScenes={runtimeScenes}
        />
      ) : sceneListOpen ? (
        <section className="scene-list-page" aria-label="场景列表">
          <div className="scene-list-header">
            <h2>场景列表</h2>
            <span>{availableScenes.length} 个场景</span>
          </div>
          <div className="scene-list-grid">
            {availableScenes.map((scene) => {
              const previewMedia = getScenePreviewMedia(scene);
              return (
                <article
                  className="scene-list-card"
                  key={scene.id}
                  onBlur={(event) => resetScenePreviewVideo(event.currentTarget)}
                  onFocus={(event) => playScenePreviewVideo(event.currentTarget)}
                  onMouseEnter={(event) => playScenePreviewVideo(event.currentTarget)}
                  onMouseLeave={(event) => resetScenePreviewVideo(event.currentTarget)}
                >
                  <span className="scene-list-video-frame" aria-hidden="true">
                    <video
                      src={previewMedia.videoUrl}
                      muted
                      loop
                      playsInline
                      preload="none"
                      poster={previewMedia.posterUrl}
                    />
                    <small>{scene.config.mode.toUpperCase()}</small>
                  </span>
                  <div className="scene-list-card-body">
                    <div className="scene-list-card-title">
                      <strong>{scene.title}</strong>
                      <small>{getSceneKindLabel(scene.sceneKind)}</small>
                    </div>
                    <p>{scene.subtitle}</p>
                    <div className="scene-list-card-footer">
                      <span>{scene.audience}</span>
                      <button type="button" onClick={() => openApplicationForm(scene)}>
                        <Link2 size={16} />
                        {SCENE_APPLICATION_CONFIG.actionLabel}
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
          {runtimeError ? <div className="connect-error">{runtimeError}</div> : null}
        </section>
      ) : selectedSceneIsPodcast && !isInCall ? (
        <PodcastStudio hostA={podcastHostA} hostB={podcastHostB} style={podcastStyle} />
      ) : (
      <section className={isInCall ? "experience in-call" : "experience user-experience"}>
        <section className={stageClassName} aria-label="实时通话体验">
          {isInCall && showTranscript ? (
            <aside className="call-profile-card" aria-label="当前角色">
              <div className="profile-status-chip" aria-hidden="true">
                <span />
                <span />
                <span />
                <small>{status === "connecting" ? "连接中" : microphoneEnabled ? "正在听" : "麦克风关"}</small>
              </div>
              <div className="profile-avatar-orbit" aria-hidden="true">
                <div className="avatar profile-avatar">
                  <video key={avatarVideoKey} src={avatarVideoUrl} autoPlay muted loop playsInline />
                </div>
              </div>
              <strong>{voiceLabel}</strong>
              <p>{selectedScene.conversationGuide}</p>
              <a>{selectedScene.title}@{selectedScene.version}</a>
            </aside>
          ) : (
            <div className="avatar-wrap" aria-hidden="true">
              <AvatarRing active={status === "connected" || status === "connecting"} />
              <div className="avatar">
                <video key={avatarVideoKey} src={avatarVideoUrl} autoPlay muted loop playsInline />
              </div>
              {isInCall ? (
                <div className="listening-bubble">
                  <span />
                  <span />
                  <span />
                  <small>{status === "connecting" ? "连接中..." : microphoneEnabled ? "正在听..." : "麦克风关"}</small>
                </div>
              ) : null}
            </div>
          )}

          {isInCall ? (
            <>
              {showTranscript ? (
                <ConversationCanvas
                  assistantFallback={assistantLine}
                  conversationGuide={selectedScene.conversationGuide}
                  eventCount={events.length}
                  events={conversationEvents}
                  latestSystemEvent={latestSystemEvent}
                  sceneTitle={selectedScene.title}
                  transcriptCue={transcriptCue}
                />
              ) : (
                <>
                  <div className="call-copy">
                    <h2>{assistantTitle}</h2>
                    <p>{assistantLine}</p>
                  </div>

                  {textComposerVisible ? (
                    <form
                      className="conversation-input"
                      onSubmit={(event) => {
                        event.preventDefault();
                        submitDraft();
                      }}
                    >
                      <Keyboard size={18} />
                      <input
                        value={draft}
                        onChange={(event) => setDraft(event.target.value)}
                        disabled={status !== "connected"}
                        placeholder={
                          connectionMode === "volcengine"
                            ? "输入文字发送 ChatTextQuery，模型会返回真实回复"
                            : "等待真实链路连接成功"
                        }
                      />
                      <button type="submit" disabled={!draft.trim() || status !== "connected"}>
                        <Send size={16} />
                        发送
                      </button>
                    </form>
                  ) : null}
                </>
              )}

              <CallControls
                elapsedText={elapsedText}
                microphoneEnabled={microphoneEnabled}
                onEndCall={endCall}
                onInterrupt={interruptPlayback}
                onToggleMicrophone={toggleMicrophone}
                onToggleRecording={toggleRecording}
                recordingEnabled={showTranscript}
                recordingToggleVisible={!platformOptions.embed}
                statusLabel={status === "connected" ? "对话中..." : statusText}
              />
            </>
          ) : (
            <>
              {scenePickerVisible ? (
                <div className="scene-grid" aria-label="场景模板">
                  {availableScenes.map((scene) => (
                    <button
                      className={selectedScene.id === scene.id ? "scene-card selected" : "scene-card"}
                      type="button"
                      key={scene.id}
                      aria-pressed={selectedScene.id === scene.id}
                      onClick={() => selectScene(scene)}
                    >
                      <span className="scene-card-topline">
                        <strong>{scene.title}</strong>
                        <small>{scene.version}</small>
                      </span>
                      <span>{scene.subtitle}</span>
                      <small>{scene.audience}</small>
                    </button>
                  ))}
                </div>
              ) : null}

              {manualStartVisible ? (
                <div className="call-actions">
                  <button className="call-button" type="button" onClick={() => void connect()} disabled={!speaker || configSaving || !sessionStartAllowed}>
                    <span>
                      <Phone size={22} />
                    </span>
                    <strong>{sessionStartAllowed ? "开始对话" : "等待创建访谈"}</strong>
                  </button>
                </div>
              ) : null}

              {lastError ? <div className="connect-error">{lastError}</div> : null}
              {runtimeError ? <div className="connect-error">{runtimeError}</div> : null}
              {callReport ? <CallReportCard report={callReport} /> : null}

            </>
          )}

        </section>
      </section>
      )}

      {applicationForm ? (
        <div className="admin-modal-backdrop" role="presentation">
          <section className="admin-modal application-modal" role="dialog" aria-modal="true" aria-label={SCENE_APPLICATION_CONFIG.modalTitle}>
            <header>
              <h3>{SCENE_APPLICATION_CONFIG.modalTitle}</h3>
              <button type="button" aria-label={SCENE_APPLICATION_CONFIG.closeLabel} onClick={() => setApplicationForm(null)}>
                <X size={18} />
              </button>
            </header>
            <div className="admin-modal-body">
              <div className="application-scene-summary">
                <span>{getSceneKindLabel(applicationForm.scene.sceneKind)}</span>
                <strong>{applicationForm.scene.title}</strong>
                <small>{applicationForm.scene.id}</small>
              </div>

              <div className="modal-grid two">
                {SCENE_APPLICATION_CONFIG.textFields.map((field) => (
                  <label className="field wide" key={field.key}>
                    <span>{field.label}</span>
                    <input
                      value={applicationForm[field.key] ?? ""}
                      onChange={(event) => updateApplicationForm({ [field.key]: event.target.value })}
                    />
                  </label>
                ))}
              </div>

              <div className="application-toggle-list">
                {SCENE_APPLICATION_CONFIG.toggleFields.map((field) => (
                  <label className="application-toggle-row" key={field.key}>
                    <input
                      type="checkbox"
                      checked={applicationForm[field.key]}
                      onChange={(event) => updateApplicationForm({ [field.key]: event.target.checked })}
                    />
                    <span>
                      <strong>{field.label}</strong>
                      <small>{field.paramName}</small>
                    </span>
                  </label>
                ))}
              </div>

              <label className="field">
                <span>{SCENE_APPLICATION_CONFIG.generatedUrlLabel}</span>
                <textarea readOnly value={buildSceneApplicationUrl(applicationForm)} />
              </label>

              <button className="primary-action" type="button" onClick={() => openApplicationUrl(applicationForm)}>
                <ExternalLink size={16} />
                {SCENE_APPLICATION_CONFIG.openUrlLabel}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
