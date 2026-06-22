import type { RealtimeConfig } from "@ai-engine/shared";
import type {
  CallLogEntry,
  CallReport,
  CreateRoleInput,
  CreateSceneInput,
  CreateSceneResult,
  CreateUserInput,
  IntentResult,
  PodcastAudioResult,
  PodcastDraft,
  RuntimeRole,
  UserProfile,
} from "../app/types";
import { isPodcastScene } from "../domain/scene/sceneKindConfig";
import type { SceneTemplate } from "../domain/scene/sceneTemplates";
import type { TestUserProfile } from "../domain/user/testUsers";
import { getBackendBaseUrl } from "./backend";

type RuntimeUsersResponse = {
  users: TestUserProfile[];
  error?: string;
};

type RuntimeScenesResponse = {
  scenes: SceneTemplate[];
  error?: string;
};

type RuntimeRolesResponse = {
  roles: RuntimeRole[];
  error?: string;
};

type RuntimeUserResponse = {
  user: TestUserProfile;
  error?: string;
};

type RuntimeRoleResponse = {
  role: RuntimeRole;
  error?: string;
};

type RuntimeSceneResponse = {
  scene: SceneTemplate;
  user?: TestUserProfile;
  error?: string;
};

type RuntimeSessionResponse = {
  user: TestUserProfile;
  scene: SceneTemplate;
  config: RealtimeConfig;
  warnings?: string[];
  error?: string;
};

type RuntimeLoginResponse = {
  user: TestUserProfile;
  scenes: SceneTemplate[];
  sessionToken: string;
  error?: string;
};

type RuntimeCallLogsResponse = {
  logs: CallLogEntry[];
  error?: string;
};

type RuntimeCallLogResponse = {
  log: CallLogEntry;
  error?: string;
};

type RuntimeIntentResponse = {
  result: IntentResult;
  error?: string;
};

type RuntimePodcastDraftResponse = {
  draft: PodcastDraft;
  error?: string;
};

type RuntimePodcastAudioResponse = {
  audio: PodcastAudioResult;
  error?: string;
};

type RuntimeUserProfileResponse = {
  profile: UserProfile;
  error?: string;
};

export async function fetchRuntimeUsers() {
  const response = await fetch(`${getBackendBaseUrl()}/runtime/users`);
  const body = (await response.json()) as RuntimeUsersResponse;
  if (!response.ok) throw new Error(body.error || "无法读取用户列表。");
  return body.users;
}

export async function fetchRuntimeRoles() {
  const response = await fetch(`${getBackendBaseUrl()}/runtime/roles`);
  const body = (await response.json()) as RuntimeRolesResponse;
  if (!response.ok) throw new Error(body.error || "无法读取角色列表。");
  return body.roles;
}

export async function loginRuntimeUser(userId: string) {
  const response = await fetch(`${getBackendBaseUrl()}/runtime/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ userId }),
  });
  const body = (await response.json()) as RuntimeLoginResponse;
  if (!response.ok || !body.user) throw new Error(body.error || "无法登录。");
  return {
    ...body,
    scenes: body.scenes.map(normalizeRuntimeScene),
  };
}

export async function fetchRuntimeScenes(userId?: string) {
  const params = userId ? `?${new URLSearchParams({ userId }).toString()}` : "";
  const response = await fetch(`${getBackendBaseUrl()}/runtime/scenes${params}`);
  const body = (await response.json()) as RuntimeScenesResponse;
  if (!response.ok) throw new Error(body.error || "无法读取场景列表。");
  return body.scenes.map(normalizeRuntimeScene);
}

export async function createRuntimeUser(operatorUserId: string, user: CreateUserInput) {
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/users`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({ operatorUserId, user }),
  });
  const body = (await response.json()) as RuntimeUserResponse;
  if (!response.ok || !body.user) throw new Error(body.error || "无法创建用户。");
  return body.user;
}

export async function updateRuntimeUser(operatorUserId: string, userId: string, user: CreateUserInput) {
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/users/${userId}`, {
    method: "PUT",
    headers: jsonHeaders(),
    body: JSON.stringify({ operatorUserId, user }),
  });
  const body = (await response.json()) as RuntimeUserResponse;
  if (!response.ok || !body.user) throw new Error(body.error || "无法修改用户。");
  return body.user;
}

export async function createRuntimeRole(operatorUserId: string, role: CreateRoleInput) {
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/roles`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({ operatorUserId, role }),
  });
  const body = (await response.json()) as RuntimeRoleResponse;
  if (!response.ok || !body.role) throw new Error(body.error || "无法创建角色。");
  return body.role;
}

export async function updateRuntimeRole(operatorUserId: string, roleId: string, role: CreateRoleInput) {
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/roles/${roleId}`, {
    method: "PUT",
    headers: jsonHeaders(),
    body: JSON.stringify({ operatorUserId, role }),
  });
  const body = (await response.json()) as RuntimeRoleResponse;
  if (!response.ok || !body.role) throw new Error(body.error || "无法修改角色。");
  return body.role;
}

export async function createRuntimeScene(operatorUserId: string, scene: CreateSceneInput) {
  const response = await fetch(`${getBackendBaseUrl()}/runtime/scenes`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({
      scene: toRuntimeScenePayload(scene),
    }),
  });
  const body = (await response.json()) as RuntimeSceneResponse;
  if (!response.ok || !body.scene || !body.user) throw new Error(body.error || "无法创建场景。");
  return {
    ...body,
    scene: normalizeRuntimeScene(body.scene),
  } as CreateSceneResult;
}

export async function updateRuntimeScene(operatorUserId: string, sceneId: string, scene: CreateSceneInput) {
  const response = await fetch(`${getBackendBaseUrl()}/runtime/scenes/${sceneId}`, {
    method: "PUT",
    headers: jsonHeaders(),
    body: JSON.stringify({
      scene: toRuntimeScenePayload(scene),
    }),
  });
  const body = (await response.json()) as RuntimeSceneResponse;
  if (!response.ok || !body.scene) throw new Error(body.error || "无法修改场景。");
  return normalizeRuntimeScene(body.scene);
}

export async function saveRuntimeSceneConfig(sceneId: string, config: RealtimeConfig) {
  const response = await fetch(`${getBackendBaseUrl()}/runtime/scenes/${sceneId}/config`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({ config }),
  });
  const body = (await response.json()) as RuntimeSceneResponse;
  if (!response.ok || !body.scene) throw new Error(body.error || "无法保存场景配置。");
  return normalizeRuntimeScene(body.scene);
}

function toRuntimeScenePayload(scene: CreateSceneInput) {
  return {
    id: scene.id,
    sceneKind: scene.sceneKind,
    title: scene.title,
    subtitle: scene.subtitle,
    audience: scene.audience,
    conversationGuide: scene.conversationGuide,
    podcastProfile: scene.sceneKind === "podcast"
      ? {
          hostA: scene.podcastHostA,
          hostB: scene.podcastHostB,
          style: scene.podcastStyle,
        }
      : undefined,
    config: {
      mode: scene.mode,
      speaker: scene.speaker,
      botName: scene.botName,
      interviewOutline: scene.interviewOutline,
      openingLine: scene.openingLine,
      systemRole: scene.systemRole,
      speakingStyle: scene.speakingStyle,
      characterManifest: scene.characterManifest,
      podcastHostA: scene.podcastHostA,
      podcastHostB: scene.podcastHostB,
      podcastStyle: scene.podcastStyle,
    },
  };
}

export async function createRuntimeSceneSession(sceneId: string, memoryEnabled: boolean) {
  const response = await fetch(`${getBackendBaseUrl()}/runtime/scene-session`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({ sceneId, memoryEnabled }),
  });
  const body = (await response.json()) as RuntimeSessionResponse;
  if (!response.ok || !body.config) throw new Error(body.error || "无法生成场景会话配置。");
  return body.scene ? { ...body, scene: normalizeRuntimeScene(body.scene) } : body;
}

function normalizeRuntimeScene(scene: SceneTemplate): SceneTemplate {
  return {
    ...scene,
    sceneKind: inferRuntimeSceneKind(scene),
  };
}

function inferRuntimeSceneKind(scene: SceneTemplate): SceneTemplate["sceneKind"] {
  if (scene.sceneKind === "dialogue" || scene.sceneKind === "podcast") return scene.sceneKind;
  return isPodcastScene(scene) ? "podcast" : "dialogue";
}

export async function saveRuntimeCallLog(
  userId: string,
  sceneId: string,
  report: CallReport,
  options: { requestId?: string; sessionId?: string } = {},
) {
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/call-logs`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({
      id: report.id,
      requestId: options.requestId,
      sessionId: options.sessionId,
      userId,
      sceneId,
      report,
    }),
  });
  const body = (await response.json()) as RuntimeCallLogResponse;
  if (!response.ok || !body.log) throw new Error(body.error || "无法保存访谈日志。");
  return body.log;
}

export async function fetchRuntimeCallLogs(userId?: string, sceneId?: string, limit = 10) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (userId) params.set("userId", userId);
  if (sceneId) params.set("sceneId", sceneId);
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/call-logs?${params.toString()}`);
  const body = (await response.json()) as RuntimeCallLogsResponse;
  if (!response.ok) throw new Error(body.error || "无法读取访谈日志。");
  return body.logs;
}

export async function classifyRuntimeIntent(text: string, userId?: string) {
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/intent`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({ text, userId }),
  });
  const body = (await response.json()) as RuntimeIntentResponse;
  if (!response.ok || !body.result) throw new Error(body.error || "无法识别对话意图。");
  return body.result;
}

export async function createPodcastDraft(input: {
  topic?: string;
  sourceText?: string;
  content?: string;
  durationMinutes?: number;
  userId?: string;
  report?: CallReport;
}) {
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/podcast/draft`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify(input),
  });
  const body = (await response.json()) as RuntimePodcastDraftResponse;
  if (!response.ok || !body.draft) throw new Error(body.error || "无法生成播客草稿。");
  return body.draft;
}

export async function createPodcastAudio(input: {
  hostA: string;
  hostB: string;
  rounds: PodcastDraft["rounds"];
  title?: string;
  userId?: string;
}) {
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/podcast/audio`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify(input),
  });
  const body = (await response.json()) as RuntimePodcastAudioResponse;
  if (!response.ok || !body.audio) throw new Error(body.error || "无法生成播客音频。");
  return body.audio;
}

export async function fetchUserProfile(userId: string, sceneId?: string) {
  const params = new URLSearchParams({ userId });
  if (sceneId) params.set("sceneId", sceneId);
  const response = await fetchWithSession(`${getBackendBaseUrl()}/runtime/user-profile?${params.toString()}`);
  const body = (await response.json()) as RuntimeUserProfileResponse;
  if (!response.ok || !body.profile) throw new Error(body.error || "无法读取用户画像。");
  return body.profile;
}

let runtimeSessionToken: string | null = null;

export function setRuntimeSessionToken(token: string | null) {
  runtimeSessionToken = token;
}

export function getRuntimeSessionToken() {
  return runtimeSessionToken;
}

export function jsonHeaders() {
  return { "content-type": "application/json" };
}

export function sessionHeaders(headers: HeadersInit = {}) {
  const nextHeaders = new Headers(headers);
  if (runtimeSessionToken) {
    nextHeaders.set("x-runtime-session", runtimeSessionToken);
  }
  return nextHeaders;
}

export function fetchWithSession(input: RequestInfo | URL, init: RequestInit = {}) {
  return fetch(input, {
    ...init,
    headers: sessionHeaders(init.headers),
  });
}
