# TODO: 播客生成

## 目标

把话题、文档摘要或通话报告转成可审核的播客轮次，优先复用豆包播客 API 的文本生成和合成能力。

## 第一版范围

- 先接 `action = 0` / `action = 4` 的 `only_nlp_text`，拿到双人播客轮次文本。
- 保存轮次为可审核脚本，不直接公开发布音频。
- 人工确认后再用 `action = 3` + `nlp_texts` 合成音频。
- 返回来源摘要、轮次、章节边界、合成建议和风险提示。

## 验收

- 输入话题可生成标题、摘要和至少 4 轮播客轮次。
- 输入材料为空时返回可读警告。
- 脚本轮次包含 `speaker`、`text`、`idx`。
- 未审核脚本不会直接生成可外发音频。
- 有单元测试覆盖轮次结构和 `nlp_texts` 转换。
- 默认播客专用 speaker：`zh_female_mizaitongxue_v2_saturn_bigtts`、`zh_male_dayixiansheng_v2_saturn_bigtts`、`zh_male_liufei_v2_saturn_bigtts`、`zh_male_xiaolei_v2_saturn_bigtts`。

## 后续

- 增加自建脚本生成器，用于高控制内容和严格来源引用。
- 保存脚本版本、来源版本和人工审核状态。
- 支持生成音频文件、章节和说话人时间轴。
- 配置火山播客服务已授权的真实 speaker ID，并用 `VOLC_PODCAST_SPEAKER_MAP` 或 `VOLC_PODCAST_SPEAKER_MIZI` 这类环境变量映射界面主持人 ID。
