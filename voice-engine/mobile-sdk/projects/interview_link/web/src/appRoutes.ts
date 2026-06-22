import { APP_CONFIG } from "./appConfig";

export type AppRoute = "interview" | "admin";

export function resolveAppRoute(pathname: string, basePath = "/"): AppRoute {
  const normalizedBase = `/${basePath.replace(/^\/+|\/+$/g, "")}`;
  const pathWithinBase = normalizedBase === "/"
    ? pathname
    : pathname.startsWith(`${normalizedBase}/`)
      ? pathname.slice(normalizedBase.length)
      : pathname;
  return pathWithinBase.replace(/\/+$/, "") === "/admin" ? "admin" : "interview";
}

export function buildPlatformInterviewUrl(platformBase: string, requestId?: string | null) {
  const params = new URLSearchParams({
    embed: APP_CONFIG.platformOptions.embed ? "1" : "0",
    recordAudio: APP_CONFIG.platformOptions.recordAudio ? "1" : "0",
    saveCallLog: APP_CONFIG.platformOptions.saveCallLog ? "1" : "0",
    showTranscript: APP_CONFIG.platformOptions.showTranscript ? "1" : "0",
    consoleTitle: APP_CONFIG.platformOptions.consoleTitle,
  });
  if (requestId) params.set("requestId", requestId);

  return `${platformBase.replace(/\/$/, "")}/scenes/${APP_CONFIG.sceneKind}/${APP_CONFIG.sceneId}?${params.toString()}`;
}

export function shouldMountPlatformFrame(requestId?: string | null) {
  return Boolean(requestId);
}
