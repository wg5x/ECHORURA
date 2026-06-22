# TODO: VAD 中途打断

## 目标

在 AI 播报过程中，通过本地 VAD 更快识别用户插话，先停止或降低当前播报，再用 ASR 文本确认是否需要向上游发送真实打断。

## 第一版范围

- 把当前基于音量阈值的 `detectUserSpeech` 抽成独立的打断候选判断模块。
- 引入本地 VAD 状态，区分 `assistant_speaking`、`user_speech_candidate`、`interrupted`、`recovering`，但不要让 VAD 直接决定对话轮次。
- 用户开口时先记录本地候选，不直接停止本地 TTS 播放；ASR 确认后再把当前 `outputId` 放入丢弃集合并打断。
- ASR 返回后再确认是否发送 `{ "type": "interrupt", "targetOutputId": "..." }`，避免把回声、背景声和“嗯/啊/哦”当成有效打断。
- 主界面不展示 `Interrupt:` 这类工程日志，只展示面向用户的状态文案。

## 验收

- AI 长句播报中，用户正常插话时，本地声音能快速停下。
- 用户只发出“嗯”“啊”等反馈音时，不频繁触发上游打断。
- 麦克风收进 AI 外放回声时，不应被误判为用户插话。
- 打断后旧音频不再漏播，新一轮 assistant 回复不被误丢。
- 主界面不再显示 `Interrupt: 用户已实时打断当前播报。`

## 后续

- 评估 WebRTC VAD、Silero VAD 或浏览器端 ONNX VAD 的准确率和包体成本。
- 使用 `AudioWorklet` 替换 `ScriptProcessorNode`，降低采集延迟。
- VAD 只作为 `user_speech_candidate` 输入接入，不重新设计对话状态机。
- 增加 VAD 命中率、误打断率和打断恢复耗时指标。
