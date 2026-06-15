# Voice Command 与 Event 协议草案

## 1. 目标

这份协议定义 Voice Engine 内部的结构化消息，避免 H5、Native Shell、Gateway、业务服务之间靠自然语言互相猜。

协议暂定为 JSON。实现时可以走 WebSocket、SSE、HTTP streaming 或 OpenAI 兼容 chunk。

第一批 JSON Schema 放在 `voice-engine/specs/schemas/`，用于约束 Gateway、Router、H5 和 Native Shell 之间的基础消息：

- `route-decision.schema.json`
- `native-action.schema.json`
- `scenario-command.schema.json`
- `voice-gateway-response.schema.json`

## 2. Route Decision

Router 每轮必须输出一个结构化决策：

```json
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
    "theme": "今天很累但还想继续努力",
    "genre": "lofi",
    "language": "zh",
    "duration_seconds": 45,
    "vocal": "female"
  }
}
```

`mode` 可选值：

| mode | 含义 |
|---|---|
| `chat` | 闲聊、帮助、解释 |
| `scenario` | 业务场景能力，例如音乐创作、内容创作、教育、客服 |
| `native_action` | 本机 Intent / Deep Link / Native Action |
| `server_action` | 服务端工具、MCP、企业 API、长任务 |
| `clarify` | 追问必要参数 |
| `reject` | 不支持或不允许 |

## 3. Native Action Command

服务端只能下发白名单动作：

```json
{
  "type": "native_action",
  "session_id": "s_001",
  "turn_id": "t_002",
  "action_id": "open_work_detail",
  "requires_confirmation": false,
  "payload": {
    "kind": "native_action",
    "screen": "work_detail",
    "work_id": "work_123"
  }
}
```

Deep Link 示例：

```json
{
  "type": "native_action",
  "session_id": "s_001",
  "turn_id": "t_003",
  "action_id": "open_deeplink",
  "payload": {
    "kind": "deeplink",
    "uri": "echorura://work/work_123"
  }
}
```

系统 Intent 示例：

```json
{
  "type": "native_action",
  "session_id": "s_001",
  "turn_id": "t_004",
  "action_id": "share_text",
  "requires_confirmation": true,
  "payload": {
    "kind": "intent",
    "action": "android.intent.action.SEND",
    "mime_type": "text/plain",
    "extras": {
      "android.intent.extra.TEXT": "听听我刚做的歌：https://echorura.com/w/work_123"
    }
  }
}
```

## 4. Scenario Command

业务场景使用统一 `scenario_command`，用 `scenario_id` 区分具体能力。音乐创作只是一个场景。

创建音乐：

```json
{
  "type": "scenario_command",
  "session_id": "s_001",
  "turn_id": "t_001",
  "scenario_id": "music_creation",
  "task_id": "task_001",
  "intent": "create_song",
  "arguments": {
    "theme": "下班路上，疲惫但继续努力",
    "genre": "lofi",
    "language": "zh",
    "duration_seconds": 45,
    "vocal": "female",
    "template_id": null
  }
}
```

修改音乐：

```json
{
  "type": "scenario_command",
  "session_id": "s_001",
  "turn_id": "t_002",
  "scenario_id": "music_creation",
  "task_id": "task_002",
  "intent": "revise_song",
  "work_id": "work_123",
  "base_version_id": "ver_001",
  "arguments": {
    "revision_prompt": "副歌更温暖一点，节奏慢一点"
  }
}
```

## 5. Event Stream

统一事件：

| 事件 | 含义 |
|---|---|
| `turn_started` | 收到用户输入 |
| `route_decision` | 路由完成 |
| `assistant_delta` | 可播报文本增量 |
| `native_action` | 下发端侧动作 |
| `native_action_result` | 端侧动作执行结果 |
| `scenario_command` | 下发业务场景命令 |
| `task_started` | 任务启动 |
| `task_progress` | 任务进度 |
| `task_result` | 任务结果 |
| `business_event_recorded` | 业务事件已记录 |
| `confirmation_required` | 需要用户确认 |
| `turn_cancelled` | 用户打断或取消 |
| `turn_completed` | 本轮完成 |
| `turn_failed` | 本轮失败 |

实时语音层需要额外把 VAD / 打断状态同步为事件，避免 H5 和 Gateway 只能依赖自然语言推断：

```json
{
  "type": "voice_interrupted",
  "session_id": "s_001",
  "turn_id": "t_001",
  "reason": "user_speech_detected",
  "cancel_current_tts": true,
  "cancel_current_task": false
}
```

任务进度示例：

```json
{
  "type": "task_progress",
  "session_id": "s_001",
  "turn_id": "t_001",
  "task_id": "task_001",
  "stage": "generating_audio",
  "message": "正在生成音频",
  "speakable": true
}
```

任务结果示例：

```json
{
  "type": "task_result",
  "task_id": "task_001",
  "work_id": "work_123",
  "version_id": "ver_001",
  "assets": {
    "audio_url": "https://cdn.echorura.com/work_123.mp3",
    "lyrics_url": "https://cdn.echorura.com/work_123.txt",
    "cover_url": "https://cdn.echorura.com/work_123.png"
  },
  "summary": "已生成一首 45 秒中文 LoFi 草稿，女声，情绪偏温暖。"
}
```

## 6. 确认协议

高风险动作必须二次确认：

```json
{
  "type": "confirmation_required",
  "confirmation_id": "confirm_001",
  "reason": "发布作品会生成公开作品页",
  "speakable_prompt": "确认发布这首作品吗？",
  "action_on_confirm": {
    "type": "publish",
    "work_id": "work_123"
  }
}
```

用户可以说：

- “确认”
- “取消”
- “先保存草稿”
- “再听一遍”
