# P3 Semantic Router 设计

## 背景

P0 到 P2 已经把实时语音 S2S、Voice Profile、`voice_turn_text` / `transcript_event` 标准化打通。P3 的核心不是继续做音乐生成，而是把稳定的用户文本转换成可审计、可测试、可复用的 `route_decision`。

这块是 Voice Engine 的核心能力，不能绑定在火山 S2S、WebSocket Gateway 或音乐场景里。音乐创作只是第一个场景，Router 必须能扩展到内容创作、教育、客服、Native 动作和服务端动作。

## 目标

- 独立实现通用 Semantic Router 模块。
- 输入文本事件，输出符合 `voice-engine/specs/schemas/route-decision.schema.json` 的 `route_decision`。
- 支持脱离 S2S 的文本测试，包括单测、CLI、HTTP 接口和前端测试页。
- 用能力注册表表达可路由能力，避免把音乐逻辑写死在 Router 主流程中。
- 第一版先跑通高确定性路由和可测试闭环，保留后续接 LLM / embedding / 混合分类器的位置。

## 非目标

- P3 不接真实音乐生成。
- P3 不实现长任务编排、作品生成、发布服务或 Native 动作执行。
- P3 不让前端或 Android 端实现意图识别逻辑。
- P3 不把 S2S 模型返回的自然语言当成业务决策来源。

## 模块边界

新增后端核心模块：

```text
voice-engine/src/api/semantic_router/
  __init__.py
  models.py
  router.py
  registry.py
  strategies.py
  cli.py
  test_router.py
```

职责边界：

- `realtime/gateway.py`：负责 S2S、WebSocket、事件收发。它只调用 Router，不包含路由判断。
- `semantic_router/router.py`：Router 门面，接收文本输入并返回 `RouteDecision`。
- `semantic_router/registry.py`：注册可路由能力，例如 `music_creation.create_song`、`native.open_page`。
- `semantic_router/strategies.py`：分类策略。第一版使用规则策略，后续可以替换或叠加 LLM 策略。
- `semantic_router/models.py`：定义输入、输出和能力描述的数据结构。
- `semantic_router/cli.py`：本地文本调试入口。

## 输入输出

Router 输入：

```json
{
  "session_id": "debug-session",
  "turn_id": "turn-1",
  "text": "帮我打开作品页",
  "source": "manual_text"
}
```

Router 输出：

```json
{
  "type": "route_decision",
  "session_id": "debug-session",
  "turn_id": "turn-1",
  "mode": "native_action",
  "intent": "open_page",
  "confidence": 0.85,
  "need_clarification": false,
  "requires_confirmation": false,
  "arguments": {
    "target": "work_detail"
  }
}
```

`mode=scenario` 时必须包含 `scenario_id` 和 `scenario_intent`。

## 能力注册表

Router 不直接写死音乐命令，而是基于能力注册表判断：

```text
Capability
- mode: scenario | native_action | server_action | chat | clarify | reject
- id: music_creation.create_song
- scenario_id: music_creation
- intent: create_song
- examples: 用户表达样例
- keywords: 高确定性触发词
- requires_confirmation: 是否需要二次确认
- argument_hints: 可抽取参数说明
```

第一版注册的能力：

| 能力 | mode | 说明 |
|---|---|---|
| `chat.general` | `chat` | 普通闲聊、问答、解释 |
| `music_creation.create_song` | `scenario` | 创建音乐草稿 |
| `music_creation.revise_song` | `scenario` | 修改当前音乐草稿 |
| `music_creation.publish_work` | `scenario` | 保存并发布作品，必须二次确认 |
| `native.open_page` | `native_action` | 打开作品页、创作页、模板页等页面 |

能力注册表是扩展点。后续新增内容创作、教育、客服时，只增加 capability 和对应测试样例，不改 Gateway 主流程。

## 路由策略

第一版采用「规则基线 + 可插拔语义策略」：

1. 先做文本清洗和归一化。
2. 用能力注册表里的高确定性关键词和样例做规则匹配。
3. 命中高风险能力时设置 `requires_confirmation=true`。
4. 低置信度时返回 `chat` 或 `clarify`，不默认触发业务动作。
5. 保留策略接口，后续可以增加 LLM 分类器，但输出仍必须通过 `route_decision` schema。

核心原则：

- 宁可少触发，也不要误触发业务动作。
- 高风险动作必须二次确认。
- Router 输出必须可记录、可回放、可测试。

## 文本测试入口

P3 必须支持不用 S2S 的文本测试。

### 单测入口

```python
decision = router.route_text(
    session_id="test-session",
    turn_id="turn-1",
    text="帮我打开作品页",
    source="unit_test",
)
```

### CLI 入口

```bash
cd voice-engine/src
.venv/bin/python -m api.semantic_router.cli "帮我打开作品页"
```

输出完整 `route_decision` JSON。

### HTTP 接口

新增文本调试接口：

```http
POST /semantic-router/decide
Content-Type: application/json

{
  "text": "帮我打开作品页",
  "session_id": "debug-session"
}
```

返回：

```json
{
  "type": "route_decision",
  "session_id": "debug-session",
  "turn_id": "turn-1",
  "mode": "native_action",
  "intent": "open_page",
  "confidence": 0.85,
  "need_clarification": false,
  "requires_confirmation": false,
  "arguments": {
    "target": "work_detail"
  }
}
```

### 前端测试页

在现有 H5 中增加一个 Router 测试视图：

- 一个文本输入框。
- 一个“识别意图”按钮。
- 一个 JSON 输出区域，展示后端返回的 `route_decision`。
- 可显示 `mode`、`intent`、`confidence`、`requires_confirmation` 的摘要。
- 这个页面只调用 `/semantic-router/decide`，不实现任何路由逻辑。

前端测试页用于产品和调试验证，不替代后端单测。

## Gateway 集成

Gateway 收到用户 ASR 文本后，事件顺序调整为：

```text
event
voice_turn_text
transcript_event
route_decision
```

只对 `role=user` 的 `voice_turn_text` 生成 `route_decision`。助手文本不进入 Router。

Gateway 失败策略：

- Router 异常时记录 error debug log。
- WebSocket 不崩溃。
- 可以返回 `mode=chat` 的降级决策或发送 error 事件。

## 验收用例

第一版必须覆盖：

| 输入文本 | 预期 |
|---|---|
| `帮我做一首下班路上听的中文 LoFi` | `mode=scenario`, `scenario_id=music_creation`, `scenario_intent=create_song` |
| `副歌慢一点` | `mode=scenario`, `scenario_id=music_creation`, `scenario_intent=revise_song` |
| `保存并发布` | `mode=scenario`, `scenario_intent=publish_work`, `requires_confirmation=true` |
| `打开作品页` | `mode=native_action`, `intent=open_page` |
| `你好` | `mode=chat` |
| `今天天气怎么样` | `mode=chat` |

前端测试页验收：

- 输入文本后能看到完整 `route_decision` JSON。
- 普通聊天和业务意图能显示不同 `mode`。
- 发布类意图能显示 `requires_confirmation=true`。

自动化验证：

- 后端 `unittest` 覆盖 Router 纯函数、HTTP 接口和 Gateway 事件顺序。
- 前端 `npm run build` 通过。

## 实施顺序

1. 建立 `semantic_router` 独立模块和数据结构。
2. 建立 capability registry 和规则策略。
3. 增加纯文本单测。
4. 增加 CLI 文本测试入口。
5. 增加 `/semantic-router/decide` HTTP 接口。
6. 把 Gateway 用户文本接入 Router。
7. 增加前端 Router 测试视图。
8. 跑后端单测和前端构建。

