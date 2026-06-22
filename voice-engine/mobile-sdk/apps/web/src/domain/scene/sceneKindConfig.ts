import type { SceneTemplate } from "./sceneTemplates";

export const SCENE_KIND_CONFIG = {
  dialogue: {
    label: "语音对话",
    shortLabel: "聊天",
  },
  podcast: {
    label: "双人播客",
    shortLabel: "播客",
  },
} as const satisfies Record<SceneTemplate["sceneKind"], { label: string; shortLabel: string }>;

export function getSceneKindLabel(sceneKind: SceneTemplate["sceneKind"]) {
  return SCENE_KIND_CONFIG[sceneKind].label;
}

export function getSceneKindShortLabel(sceneKind: SceneTemplate["sceneKind"]) {
  return SCENE_KIND_CONFIG[sceneKind].shortLabel;
}

export function isPodcastSceneKind(sceneKind: SceneTemplate["sceneKind"]) {
  return sceneKind === "podcast";
}

type PodcastSceneShape = Pick<SceneTemplate, "podcastProfile" | "requiredCapabilities" | "sceneKind"> & {
  config: Partial<Pick<SceneTemplate["config"], "podcastHostA" | "podcastHostB" | "podcastStyle">>;
};

export function isPodcastScene(scene: PodcastSceneShape) {
  return (
    isPodcastSceneKind(scene.sceneKind)
    || scene.requiredCapabilities.includes("podcast_generation")
    || scene.requiredCapabilities.includes("podcast_voice_pair")
    || Boolean(scene.podcastProfile)
    || Boolean(scene.config.podcastHostA || scene.config.podcastHostB || scene.config.podcastStyle)
  );
}
