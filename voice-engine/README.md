# ECHORURA Voice Engine

`voice-engine` 是 ECHORURA 后续落地语音优先交互的通用工程目录。

它不是只服务音乐创作的单点模块，而是一个可复用的语音行动引擎：

> 通过语音会话、语义路由、H5/Native Bridge、任务编排和事件协议，让不同业务场景都能获得“说话 -> 理解 -> 执行 -> 反馈”的闭环能力。

ECHORURA 音乐创作是第一条落地场景，后续可以扩展到无障碍内容创作、客服、教育、工具操作、设备控制等场景。

## 目录

```text
voice-engine/
  README.md
  docs/
    product-scope.md
    technical-architecture.md
    doubao-realtime-voice-plan.md
    assets/diagrams/voice-engine-architecture.mmd
  specs/
    voice-command-event-protocol.md
    schemas/
  adr/
    0001-android-first-voice-engine.md
```

## 当前文档

- [产品边界](docs/product-scope.md)：明确通用 Voice Engine 做什么、不做什么，以及音乐创作场景的 MVP 边界。
- [技术架构](docs/technical-architecture.md)：H5-first + Android Native Shell 的通用语音引擎架构。
- [豆包实时语音落地方案](docs/doubao-realtime-voice-plan.md)：基于火山/豆包官方实时语音样例，拆解 S2S、VAD、打断、CustomLLM 和意图识别的接入路径。
- [命令与事件协议](specs/voice-command-event-protocol.md)：H5、Native Shell、Gateway、业务服务之间的结构化协议草案。
- [架构图](docs/assets/diagrams/voice-engine-architecture.mmd)：Mermaid 架构图源文件。
- [ADR-0001](adr/0001-android-first-voice-engine.md)：为什么主路径选择 Android Intent / Native Action，而不是云手机。

## 实现原则

- H5 承载主要业务页面，Android WebView + Native Shell 提供语音、权限、Intent、分享、文件选择等系统能力。
- Voice Engine 核心保持通用：会话、语音、路由、确认、事件流、H5/Native Bridge、能力调度。
- 第一阶段先做 S2S 可对话语音入口，让用户能自然说话并听到实时回复。
- 第二阶段再做 VAD / 打断，把插话、取消播报、取消当前 turn 的体验打磨稳定。
- 第三阶段再做意图识别和业务路由，把稳定的对话输入转成 `route_decision`、`scenario_command`、`native_action` 等结构化事件。
- 业务能力通过场景模块接入，例如 `music_creation`、`content_creation`、`education`、`support`。
- 云手机 / mobile-use 不进入主路径，只作为远程代执行或无用户设备在线时的兜底能力。
- 视觉障碍和低操作门槛体验优先，关键流程必须能被语音、键盘和屏幕阅读器完成。
- Web3 属于业务场景能力，不进入 Voice Engine 核心；音乐场景只把作品、模板、版本和二创关系作为事件记录。
