import type { SceneTemplate } from "./sceneTemplates";
import { getSceneKindShortLabel } from "./sceneKindConfig";
import { buildSceneApplicationPath, type SceneApplicationParams } from "./sceneRoutes";

export type SceneApplicationForm = SceneApplicationParams & {
  scene: SceneTemplate;
};

export type SceneApplicationTextFieldKey = "consoleTitle" | "requestId";
export type SceneApplicationToggleFieldKey = "recordAudio" | "saveCallLog" | "showTranscript";

export const SCENE_APPLICATION_CONFIG = {
  actionLabel: "创建应用",
  closeLabel: "关闭",
  generatedUrlLabel: "生成链接",
  modalTitle: "创建应用",
  openUrlLabel: "打开应用链接",
  requestIdPrefix: "app",
  textFields: [
    { key: "consoleTitle", label: "页面标题" },
    { key: "requestId", label: "requestId" },
  ],
  toggleFields: [
    { key: "recordAudio", label: "录音", paramName: "recordAudio", defaultValue: true },
    { key: "saveCallLog", label: "保存日志", paramName: "saveCallLog", defaultValue: true },
    { key: "showTranscript", label: "显示转写", paramName: "showTranscript", defaultValue: false },
  ],
} as const satisfies {
  actionLabel: string;
  closeLabel: string;
  generatedUrlLabel: string;
  modalTitle: string;
  openUrlLabel: string;
  requestIdPrefix: string;
  textFields: ReadonlyArray<{ key: SceneApplicationTextFieldKey; label: string }>;
  toggleFields: ReadonlyArray<{
    key: SceneApplicationToggleFieldKey;
    label: string;
    paramName: string;
    defaultValue: boolean;
  }>;
};

export function createSceneApplicationForm(scene: SceneTemplate, requestSeed: string): SceneApplicationForm {
  return {
    scene,
    consoleTitle: scene.title,
    requestId: buildSceneApplicationRequestId(scene, requestSeed),
    ...getSceneApplicationToggleDefaults(),
  };
}

export function buildSceneApplicationUrl(form: SceneApplicationForm) {
  return buildSceneApplicationPath(form.scene, form);
}

export function getSceneKindLabel(sceneKind: SceneTemplate["sceneKind"]) {
  return getSceneKindShortLabel(sceneKind);
}

function getSceneApplicationToggleDefaults(): Record<SceneApplicationToggleFieldKey, boolean> {
  return Object.fromEntries(
    SCENE_APPLICATION_CONFIG.toggleFields.map((field) => [field.key, field.defaultValue]),
  ) as Record<SceneApplicationToggleFieldKey, boolean>;
}

function buildSceneApplicationRequestId(scene: Pick<SceneTemplate, "id">, requestSeed: string) {
  return `${SCENE_APPLICATION_CONFIG.requestIdPrefix}_${sanitizeIdentifier(scene.id)}_${sanitizeIdentifier(requestSeed).slice(0, 12)}`;
}

function sanitizeIdentifier(value: string) {
  return value.replace(/[^a-zA-Z0-9_-]/g, "_");
}
