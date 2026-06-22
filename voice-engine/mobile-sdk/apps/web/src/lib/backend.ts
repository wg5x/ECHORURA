function getConfiguredBackendBaseUrl() {
  const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
  return env?.VITE_API_BASE_URL?.replace(/\/$/, "");
}

export function getBackendBaseUrl() {
  const configuredUrl = getConfiguredBackendBaseUrl();
  if (configuredUrl) return configuredUrl;

  if (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") {
    return `${window.location.protocol}//${window.location.hostname}:8787`;
  }

  return `${window.location.origin}/api`;
}

export function getBackendWsUrl(path: string) {
  const baseUrl = new URL(getBackendBaseUrl(), window.location.origin);
  baseUrl.protocol = baseUrl.protocol === "https:" ? "wss:" : "ws:";
  baseUrl.pathname = path;
  baseUrl.search = "";
  return baseUrl.toString();
}
