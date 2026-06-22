export const PODCAST_HOST_OPTIONS = [
  { id: "mizi", label: "黑猫侦探社咪仔", description: "女声主持" },
  { id: "dayi", label: "大壹先生", description: "男声主持" },
  { id: "liufei", label: "刘飞", description: "访谈男声" },
  { id: "xiaolei", label: "潇磊", description: "解读男声" },
] as const;

export const DEFAULT_PODCAST_PROFILE = {
  hostA: PODCAST_HOST_OPTIONS[0].id,
  hostB: PODCAST_HOST_OPTIONS[1].id,
  style: "双人播客解读",
} as const;
