# Agent Profile Config Design

## Purpose

把 voice-engine 的可配置项拆成三个独立配置域，每个域管理一个清楚的维度。Agent Profile 组合它们，定义一个具体运行时 Agent 的人格与能力边界。

## Design

### Voice Profile

管理“怎么说”的配置。一个 Voice Profile 包含：

| Field | Type | Description |
|-------|------|-------------|
| id | string | Stable identifier |
| name | string | Human-readable label |
| speaker | string | TTS speaker ID |
| systemRole | string | System prompt / persona text |
| speakingStyle | string | Style hint for TTS model |
| openingLine | string | First utterance after session start |
| enableWebSearch | bool | Whether to enable internet search |
| enableMusic | bool | Whether to enable singing |
| extra | object | Provider-specific overrides (e.g. O2 params) |

A system might have several Voice Profiles:
- Music Companion
- Concise Tool Agent
- Customer Support
- Educational Tutor

### Capability

管理“能做什么”的配置。一个 Capability 包含：

| Field | Type | Description |
|-------|------|-------------|
| id | string | Stable identifier, dot-notation e.g. native.call_phone |
| name | string | Human-readable label |
| description | string | What this capability does |
| mode | enum | chat / scenario / native_action / server_action |
| scenario_id | string | Scenario namespace, e.g. music_creation |
| scenario_intent | string | Intent within scenario, e.g. create_song |
| intent | string | General intent label |
| keywords | string[] | Trigger keywords |
| example_sentences | string[] | Representative inputs for testing |
| argument_schema | object | JSON Schema for extracted arguments |
| parameter_extractor | string | Identifier for parameter extraction strategy |
| risk_level | enum | low / medium / high |
| requires_confirmation | bool | Must confirm before executing |
| enabled | bool | Whether this capability is active |

Examples:
- `native.call_phone`: keywords "打电话", extract phone_number
- `native.open_page`: keywords "打开页面", arguments {"target": "work_detail"}
- `music_creation.create_song`: keywords "做一首歌", extract genre/vocal/theme
- `music_creation.revise_song`: keywords "副歌慢一点", extract revision_prompt
- `chat.general`: no keywords, fallback

### Agent Profile

管理“用哪些配置来运行哪个 Agent”的组合配置。一个 Agent Profile 包含：

| Field | Type | Description |
|-------|------|-------------|
| id | string | Stable identifier |
| name | string | Human-readable name |
| description | string | What this Agent does |
| voice_profile_id | string | Reference to Voice Profile |
| enabled_capability_ids | string[] | References to enabled Capabilities |
| routing_policy | object | Fallback mode, confidence threshold, multi-intent behavior |
| safety_policy | object | Confirmation rules, blocked intents, risk level cap |
| default_chat_mode | enum | Whether unmatched inputs go to chat or clarify |
| ui_entry | string | Default page / tab for this Agent |
| context_sources | string[] | Which context scopes are available |

Examples:
- Phone Assistant: Tool voice + call / open / share capabilities + high-confirmation policy
- Music Creator: Warm voice + create / revise / publish capabilities + confirm publish
- Customer Support: Neutral voice + ticket / order capabilities + read-only until confirmed

### Relationship

```
Voice Profile ──┐
                ├── Agent Profile ──→ Runtime (Gateway + Router)
Capability    ──┘
```

## Scope

Stage 1: All three domains are code-configured (Python dataclasses / TS objects). Tests exercise them through the existing CLI and HTTP text endpoints. No frontend management UI yet.

Stage 2: Add simple JSON/YAML configuration loading for Voice Profile and Capability. Agent Profile stays in code.

Stage 3: Build three dedicated configuration pages in the web app, plus a simple REST API to read current configuration.

## Success Criteria

- Each of the three domains has a clearly defined structure and stable identifier
- Agent Profile routes correctly within the capabilities it references
- A text test can be run against any Agent Profile to verify route decisions
- Adding a new capability does not require changing Router core logic
