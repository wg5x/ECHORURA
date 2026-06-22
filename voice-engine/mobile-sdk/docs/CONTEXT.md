# CONTEXT

本文档记录 ai-engine 当前代码里的领域语言，避免后续扩展时同一个概念出现多个名字。

## 领域词

| 术语 | 含义 |
| --- | --- |
| Web H5 | 当前 `apps/web` 应用。浏览器和未来 Android WebView 都加载同一套 Web。 |
| Android Shell | 后续可新增的 Android 原生壳子，只负责承载 Web H5、权限、设备能力和分发。 |
| Runtime User | 运行时用户视角，决定可访问的场景、账号角色和用户上下文。 |
| Runtime Scene | 可运行的语音场景，包含模型、音色、提示词、安全策略、记忆策略和报告策略。 |
| Voice Session | 一次实时语音通话，从 WebSocket start 到 finish。 |
| Realtime Gateway | 后端 WebSocket 适配层，连接 Web H5 和火山/豆包实时语音上游。 |
| Volc Adapter | `apps/api/integrations/volc` 中的火山/豆包协议、事件和帧格式适配。 |
| Memory Card | 本地压缩记忆卡，会后从转写压缩，下次按开关注入到提示词。 |
| Call Report | 通话结束后的本地报告，包含摘要、轮次、转写和运行指标。 |

## 当前决策

- `apps/web` 是共享 Web H5，不按浏览器和 Android 分裂两套前端。
- Android 壳子放在 `apps/android/`，当前只做 WebView 容器，并加载部署 URL。
- 当前 TypeScript 共享类型放在 `apps/web/src/shared`；只有真的被多个一级 app 复用时，才重新引入独立 package。
- 本地运行数据放在 `apps/api/.local/runtime/`，不要放在根目录 `tmp/` 或根目录 `.local/`。
