import type { SceneTemplate } from "./sceneTemplates";

export const SCENE_ROUTE_PREFIX = "/scenes";

export type SceneRouteMatch = {
  canonicalPath: string;
  platformOptions: PlatformRouteOptions;
  scene: SceneTemplate;
  sceneKind: SceneTemplate["sceneKind"];
};

export type PlatformRouteOptions = {
  app: boolean;
  consoleTitle?: string;
  embed: boolean;
  recordAudio: boolean;
  requestId?: string;
  saveCallLog: boolean;
  showTranscript: boolean;
  trial: boolean;
};

export const DEFAULT_PLATFORM_ROUTE_OPTIONS: PlatformRouteOptions = {
  app: false,
  embed: false,
  recordAudio: false,
  saveCallLog: true,
  showTranscript: true,
  trial: false,
};

export function buildScenePath(scene: Pick<SceneTemplate, "id" | "sceneKind">) {
  return `${SCENE_ROUTE_PREFIX}/${scene.sceneKind}/${scene.id}`;
}

export type SceneApplicationParams = {
  consoleTitle?: string;
  recordAudio: boolean;
  requestId?: string;
  saveCallLog: boolean;
  showTranscript: boolean;
};

export function buildSceneApplicationPath(
  scene: Pick<SceneTemplate, "id" | "sceneKind">,
  application: SceneApplicationParams,
) {
  const params = new URLSearchParams({
    embed: "1",
    app: "1",
    recordAudio: application.recordAudio ? "1" : "0",
    saveCallLog: application.saveCallLog ? "1" : "0",
    showTranscript: application.showTranscript ? "1" : "0",
  });
  const consoleTitle = parseDisplayTextParam(application.consoleTitle ?? null);
  if (consoleTitle) params.set("consoleTitle", consoleTitle);
  const requestId = parseRequestId(application.requestId ?? null);
  if (requestId) params.set("requestId", requestId);
  return `${buildScenePath(scene)}?${params.toString()}`;
}

export function isSceneListRoute(pathname: string) {
  return pathname.replace(/\/+$/, "") === SCENE_ROUTE_PREFIX;
}

export function getSceneListRedirectPath(pathname: string) {
  return pathname === "/" || pathname === "" ? SCENE_ROUTE_PREFIX : null;
}

export function resolveSceneRoute(pathname: string, search: string, scenes: SceneTemplate[]): SceneRouteMatch | null {
  const parts = pathname.split("/").filter(Boolean);
  if (parts[0] !== "scenes" || parts.length < 3) return null;

  const requestedKind = parts[1];
  const sceneId = parts[2];
  if (requestedKind !== "dialogue" && requestedKind !== "podcast") return null;

  const scene = scenes.find((item) => item.id === sceneId);
  if (!scene) return null;

  return {
    canonicalPath: buildScenePath(scene),
    platformOptions: parsePlatformRouteOptions(search),
    scene,
    sceneKind: scene.sceneKind,
  };
}

export function parsePlatformRouteOptions(search: string): PlatformRouteOptions {
  const params = new URLSearchParams(search);
  const options: PlatformRouteOptions = {
    app: parseBooleanParam(params.get("app"), DEFAULT_PLATFORM_ROUTE_OPTIONS.app),
    embed: parseBooleanParam(params.get("embed"), DEFAULT_PLATFORM_ROUTE_OPTIONS.embed),
    recordAudio: parseBooleanParam(params.get("recordAudio"), DEFAULT_PLATFORM_ROUTE_OPTIONS.recordAudio),
    requestId: parseRequestId(params.get("requestId")),
    saveCallLog: parseBooleanParam(params.get("saveCallLog"), DEFAULT_PLATFORM_ROUTE_OPTIONS.saveCallLog),
    showTranscript: parseBooleanParam(params.get("showTranscript"), DEFAULT_PLATFORM_ROUTE_OPTIONS.showTranscript),
    trial: parseBooleanParam(params.get("trial"), DEFAULT_PLATFORM_ROUTE_OPTIONS.trial),
  };
  const consoleTitle = parseDisplayTextParam(params.get("consoleTitle"));
  if (consoleTitle) options.consoleTitle = consoleTitle;
  return options;
}

export function shouldShowScenePicker(platformOptions: Pick<PlatformRouteOptions, "embed">) {
  return !platformOptions.embed;
}

export function canStartPlatformSession(platformOptions: Pick<PlatformRouteOptions, "embed" | "requestId">) {
  return !platformOptions.embed || Boolean(platformOptions.requestId);
}

export function shouldShowTextComposer(platformOptions: Pick<PlatformRouteOptions, "embed">) {
  return !platformOptions.embed;
}

export function shouldShowManualStartButton(
  platformOptions: Pick<PlatformRouteOptions, "embed"> & Partial<Pick<PlatformRouteOptions, "app" | "trial">>,
) {
  return !platformOptions.embed || Boolean(platformOptions.trial) || Boolean(platformOptions.app);
}

function parseBooleanParam(value: string | null, fallback: boolean) {
  if (value === null) return fallback;
  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  return fallback;
}

function parseRequestId(value: string | null) {
  const text = value?.trim() ?? "";
  if (!text || !/^[a-zA-Z0-9_-]{1,100}$/.test(text)) return undefined;
  return text;
}

function parseDisplayTextParam(value: string | null) {
  const text = value?.trim() ?? "";
  if (!text) return undefined;
  return text.slice(0, 40);
}
