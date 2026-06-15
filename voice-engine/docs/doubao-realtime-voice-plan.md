# 豆包实时语音落地方案

目标：基于火山/豆包官方实时语音能力和示例，完成 Voice Engine 的基础能力：

- 实时语音输入
- VAD / 打断
- 低延迟语音反馈
- 意图识别
- H5 / Android Native Bridge
- 场景能力调度

## 1. 结论

Voice Engine 的基础能力建议分三步做，而不是一开始就做完整业务路由：

```text
H5 / Android WebView
  -> Android Native Shell / Web RTC Client
  -> 豆包 S2S 实时语音
  -> VAD / 打断
  -> Voice Gateway / Semantic Router
  -> Scenario Skill / Native Action
```

其中：

- 第一阶段先做 S2S 可对话入口，只验证“用户能说，系统能实时语音回答”。
- 第二阶段做 VAD / 打断，只验证“用户能插话，系统能停播或取消当前 turn”。
- 第三阶段再做意图识别、业务路由、确认、安全边界和场景插件。
- 音乐创作只是第一个 `music_creation` 场景，Voice Engine 本身保持通用。

## 2. 为什么不直接把 S2S 当全部大脑

豆包端到端实时语音模型适合自然、拟人、低延迟的语音对话。官方产品介绍中也强调 S2S-Omni 是低延时语音端到端助手模型，支持随时打断、主动搭话、语音控制等能力。

但 Voice Engine 需要稳定执行业务动作：

- `create_song`
- `revise_song`
- `choose_template`
- `publish_work`
- `native_action`
- `server_action`
- `confirmation_required`

这些动作需要结构化、可审计、可回放、可测试。因此不建议把 S2S 模型直接作为全部大脑，而应让它承担语音交互体验，把业务判断交给自己的 Semantic Router。

## 3. 推荐主路径

### 3.1 第一阶段：S2S 可对话语音入口

优先参考豆包实时语音模型，先跑通端到端语音对话。

原因：

- 语音入口是这个项目的第一体验，必须先证明“可以自然说话”。
- S2S 更接近用户感知，不需要先拆 ASR、LLM、TTS 级联。
- 对视觉障碍和低操作门槛用户来说，低延迟、自然响应比第一天就能执行业务动作更重要。

适合 Voice Engine 的原因：

- 先把麦克风、音频播放、连接稳定性、会话状态和延迟打通。
- H5 / Android WebView 可以先围绕一个“对话按钮 + 状态提示 + 字幕旁路”做最小体验。
- 后续加 VAD、意图识别、场景动作时，不会推翻语音入口。

### 3.2 第二阶段：VAD / 打断

在 S2S 对话跑通以后，再重点做打断体验：

- 用户插话时停止当前播报。
- 用户说“停一下”“重来”“取消”时取消当前 turn。
- H5 同步显示 `voice_interrupted`、`turn_cancelled` 等状态。
- Android Shell 后续处理音频焦点、麦克风权限和后台状态。

### 3.3 第三阶段：意图识别和业务路由

等语音体验稳定后，再把自然语言转成结构化事件：

- `route_decision`
- `scenario_command`
- `native_action`
- `confirmation_required`

强业务动作必须落到结构化事件：

```json
{
  "type": "route_decision",
  "mode": "scenario",
  "scenario_id": "music_creation",
  "scenario_intent": "create_song",
  "requires_confirmation": false
}
```

## 4. 官方示例参考

### 4.1 `rtc-aigc-demo`

用途：

- 跑通 RTC + ASR + LLM + TTS 的实时语音链路。
- 理解火山 RTC 对话式 AI 的配置方式。
- 参考场景配置和服务端接入方式。
- 验证 Web 端麦克风、RTC Token、ASR/TTS、VAD、打断和端到端延迟。

仓库：

- https://github.com/volcengine/rtc-aigc-demo

官方 README 中的关键信息：

- Node 版本要求：16.0+。
- 需要分别启动服务端和前端页面。
- 跑通阶段重点填 `Server/scenes/*.json`，不用先深改代码。
- 场景 JSON 主要包括 `SceneConfig`、`AccountConfig`、`RTCConfig`、`VoiceChat`。
- `RTCConfig` 中的 AppId、AppKey 来自 RTC AIGC 控制台；RoomId、UserId 可以自定义或由服务端生成。
- `VoiceChat` 用于配置 ASR、LLM、TTS 等 AIGC 参数。

建议使用方式：

1. 不把它作为第一刀。
2. S2S 入口跑通后，用它对比 RTC + ASR + LLM + TTS 级联体验。
3. 当需要更强文本控制或 CustomLLM 回调时，再使用 `Server/scenes/Custom.json` 作为 ECHORURA 场景配置入口。
4. 将 CustomLLM 回调指向本项目的 Voice Gateway。
5. Voice Gateway 返回可播报文本，同时输出结构化事件。

最小接入假设：

```text
rtc-aigc-demo Server
  -> CustomLLM HTTP 回调
  -> ECHORURA Voice Gateway
  -> Semantic Router
  -> speakable_text + events
```

Voice Gateway 不应该返回“自然语言里夹带业务动作”，而应该返回：

```json
{
  "session_id": "s_001",
  "turn_id": "t_001",
  "speakable_text": "好的，我先帮你生成一版 45 秒中文 LoFi 草稿。",
  "events": [
    {
      "type": "route_decision",
      "session_id": "s_001",
      "turn_id": "t_001",
      "mode": "scenario",
      "intent": "create_song",
      "scenario_id": "music_creation",
      "scenario_intent": "create_song",
      "confidence": 0.92,
      "need_clarification": false,
      "requires_confirmation": false,
      "arguments": {
        "genre": "lofi",
        "language": "zh",
        "duration_seconds": 45
      }
    }
  ]
}
```

需要在官方 Demo 中确认的改造点：

| 改造点 | 要确认的问题 | ECHORURA 处理 |
|---|---|---|
| 场景配置 | `VoiceChat` 如何配置自定义 LLM | 新增 ECHORURA Custom 场景 |
| 鉴权 | CustomLLM 回调是否支持自定义 Header / Token | Gateway 增加签名校验 |
| 入参 | 回调是否包含文本、上下文、用户和房间信息 | 统一映射为 `session_id`、`turn_id`、`text` |
| 出参 | 返回文本是否会直接进入 TTS | 返回 `speakable_text`，事件旁路给 H5 / 后端 |
| 打断 | VAD 打断是否有事件或状态回调 | 映射为 `voice_interrupted` / `turn_cancelled` |
| 多轮 | 上下文由官方链路维护还是由 Gateway 维护 | Gateway 自己维护业务上下文 |

### 4.2 火山引擎实时对话式 AI 文档

用途：

- 理解 RTC 对话式 AI 的能力边界。
- 确认如何启动、更新、停止语音会话。
- 确认如何处理 AI 状态、任务事件、打断、噪声处理、字幕和上下文。

参考：

- https://www.volcengine.com/docs/82379/1393085

### 4.3 豆包实时语音模型文档

用途：

- 评估 S2S-Omni / S2S-SC 的适用场景。
- 评估端到端语音模型对 Voice Engine 的价值。

参考：

- https://www.volcengine.com/docs/6561/1594360
- https://seed.bytedance.com/zh/blog/%E8%B1%86%E5%8C%85%E5%AE%9E%E6%97%B6%E8%AF%AD%E9%9F%B3%E5%A4%A7%E6%A8%A1%E5%9E%8B%E4%B8%8A%E7%BA%BF%E5%8D%B3%E5%BC%80%E6%94%BE-%E6%83%85%E5%95%86%E6%99%BA%E5%95%86%E5%8F%8C%E9%AB%98

## 5. Voice Engine 基础能力拆分

### 5.1 实时语音层

职责：

- 建立实时语音会话。
- 接收用户语音。
- 支持 VAD、打断、降噪。
- 输出可播报语音。
- 将用户输入和 AI 回复以事件形式同步给 H5。

第一阶段建议：

- 直接复用火山 RTC 对话式 AI。
- 如果 H5 Web 端先做 Demo，可以先走 Web RTC。
- Android WebView Shell 后续承接麦克风、音频焦点、权限和系统能力。

### 5.2 Voice Gateway

职责：

- 第一阶段不强依赖 Gateway，S2S 可以先直连语音入口 Demo。
- 第二阶段接收 S2S / VAD 旁路事件，例如转写文本、打断状态、会话状态。
- 第三阶段接收 CustomLLM 回调或语音转写文本。
- 管理 `session_id`、`turn_id`、用户状态和上下文。
- 调用 Semantic Router。
- 返回可播报文本。
- 同步结构化事件给 H5。

输入：

```json
{
  "session_id": "s_001",
  "turn_id": "t_001",
  "room_id": "rtc_room_001",
  "user_id": "user_001",
  "text": "帮我做一首下班路上听的中文 LoFi",
  "source": "volcengine_rtc_custom_llm"
}
```

输出：

```json
{
  "speakable_text": "好的，我先帮你生成一版 45 秒中文 LoFi 草稿。",
  "events": [
    {
      "type": "route_decision",
      "session_id": "s_001",
      "turn_id": "t_001",
      "mode": "scenario",
      "scenario_id": "music_creation",
      "scenario_intent": "create_song"
    },
    {
      "type": "scenario_command",
      "session_id": "s_001",
      "turn_id": "t_001",
      "scenario_id": "music_creation",
      "intent": "create_song"
    }
  ]
}
```

### 5.3 Semantic Router

职责：

- 把自然语言转成结构化意图。
- 判断是否需要澄清。
- 判断是否需要二次确认。
- 区分通用动作和业务场景动作。

第一批意图：

- `chat`
- `clarify`
- `native_action`
- `server_action`
- `scenario`
- `reject`

第一批音乐场景意图：

- `create_song`
- `revise_song`
- `choose_template`
- `publish_work`
- `record_idea`

### 5.4 H5 / Native Bridge

职责：

- H5 负责业务界面。
- Android Native Shell 负责系统能力。
- Bridge 负责能力调用和事件回传。

第一批 Native 能力：

- `startVoiceSession`
- `stopVoiceSession`
- `requestMicPermission`
- `speak`
- `shareWork`
- `pickAudioFile`
- `openSettings`

第一批 H5 事件：

- `voice.session_started`
- `voice.partial_text`
- `voice.final_text`
- `voice.interrupted`
- `voice.response_delta`
- `route.decision`
- `task.progress`
- `task.result`
- `confirmation.required`
- `native.result`

## 6. 建议 PoC 顺序

### P0：S2S 可对话入口

目标：

- 跑通豆包 S2S 实时语音对话。
- 用户能按住或点击开始说话。
- 系统能用语音实时回复。
- H5 能显示连接、录音、播放、错误等基础状态。

输出：

- 必需凭证清单。
- Demo 运行记录。
- S2S 连接方式、鉴权方式、音频格式记录。
- 首包延迟、完整回复延迟、断线重连记录。

验收：

- 用户说“你好，陪我聊两句”，系统能语音回答。
- 用户连续问两轮，系统能保持基础上下文。
- H5 能显示 `connecting`、`listening`、`speaking`、`error`。

### P1：VAD / 打断

目标：

- 用户插话时，系统停止当前播报。
- 用户说“停一下”“取消”“重来”时，当前 turn 被取消或重置。
- H5 能收到打断事件。

验收：

- 播报过程中用户说话，播报停止。
- H5 收到 `voice_interrupted`。
- 当前 turn 状态能从 `speaking` 回到 `listening`。

### P2：加入意图识别

目标：

- Router 能识别 `chat`、`create_song`、`revise_song`、`publish_work`。
- 输出 `route_decision`。

验收：

- “帮我做一首歌” -> `music_creation.create_song`
- “副歌慢一点” -> `music_creation.revise_song`
- “保存并发布” -> `music_creation.publish_work` + `requires_confirmation`
- “打开作品页” -> `native_action`

### P3：CustomLLM / Voice Gateway 旁路

目标：

- 如果 S2S 支持稳定文本旁路或 function calling，则把它接入 Gateway。
- 如果 S2S 不能稳定输出结构化事件，则用 RTC + ASR/TTS + CustomLLM 作为业务路由补充链路。
- Gateway 输出符合 `voice-gateway-response.schema.json`。

验收：

- Gateway 收到文本或语义事件。
- Gateway 返回可播报文本。
- H5 收到 `turn_started`、`route_decision`、`turn_completed`。

### P4：接 Mock Music Skill

目标：

- 不接真实音乐生成。
- 返回固定音频、歌词、标题、封面。
- 跑通发布页和 lineage 记录。

验收：

- 用户能通过语音完成 create -> revise -> publish。
- 每一步都有语音反馈。
- H5 显示任务进度。
- 后台记录 `work_id`、`version_id`、`template_id`。

### P5：接真实音乐生成

目标：

- 替换 Mock Provider。
- 保持协议不变。
- 对长任务给出进度反馈。

## 7. 需要确认的技术问题

1. 火山 RTC 对话式 AI 的 CustomLLM 回调格式和鉴权方式。
2. H5 是否直接接 RTC SDK，还是通过 Android Native Shell 接。
3. Android WebView 下麦克风、音频焦点、后台播放的权限和兼容性。
4. VAD / 打断事件如何传给 H5 和 Gateway。
5. S2S 模型是否支持稳定 function calling / 结构化业务事件；如果不稳定，就只用于自然对话体验。
6. Gateway 是否采用 Arkitect，还是先用轻量 Node/Python 服务。

## 8. 推荐工程落点

建议新增：

```text
voice-engine/
  h5/
  android-shell/
  gateway/
    router/
    scenarios/
      music_creation/
    providers/
      volcengine/
        rtc/
        s2s/
  specs/
    schemas/
```

第一版可以更小：

```text
voice-engine/
  h5/
  gateway/
  specs/
```

Android Native Shell 等 H5 Demo 跑通后再接入。
