# Semantic Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a generic, independent, text-testable Semantic Router that converts text into `route_decision` and exposes it through unit tests, CLI, HTTP, Gateway events, and a frontend test view.

**Architecture:** Add `api.semantic_router` as a standalone core module with typed dataclasses, a capability registry, and a deterministic rule strategy. The realtime Gateway will call this module after emitting user `voice_turn_text`; the frontend will call a separate HTTP debug endpoint for text-only testing.

**Tech Stack:** Python 3.11, FastAPI, unittest, React, TypeScript, Vite.

---

## File Map

- Create `voice-engine/src/api/semantic_router/__init__.py`: export the public Router API.
- Create `voice-engine/src/api/semantic_router/models.py`: dataclasses for router input, decisions, and capabilities.
- Create `voice-engine/src/api/semantic_router/registry.py`: default capability registry.
- Create `voice-engine/src/api/semantic_router/strategies.py`: deterministic rule-based classifier.
- Create `voice-engine/src/api/semantic_router/router.py`: public `SemanticRouter.route_text()` facade.
- Create `voice-engine/src/api/semantic_router/cli.py`: text-only CLI debug entry.
- Create `voice-engine/src/api/semantic_router/test_router.py`: unit tests for routing behavior.
- Modify `voice-engine/src/api/main.py`: add `/semantic-router/decide`.
- Modify `voice-engine/src/api/realtime/gateway.py`: emit `route_decision` after user transcript events.
- Modify `voice-engine/src/api/realtime/test_gateway.py`: assert Gateway emits `route_decision`.
- Modify `voice-engine/src/web/src/app/App.tsx`: add a router test view.
- Modify `voice-engine/src/web/src/app/styles.css`: style the router test controls and JSON output.

## Task 1: Core Router Models And Registry

**Files:**
- Create: `voice-engine/src/api/semantic_router/__init__.py`
- Create: `voice-engine/src/api/semantic_router/models.py`
- Create: `voice-engine/src/api/semantic_router/registry.py`
- Create: `voice-engine/src/api/semantic_router/strategies.py`
- Create: `voice-engine/src/api/semantic_router/router.py`
- Test: `voice-engine/src/api/semantic_router/test_router.py`

- [ ] **Step 1: Write failing router tests**

Create `voice-engine/src/api/semantic_router/test_router.py` with these tests:

```python
import unittest

from .router import SemanticRouter


class SemanticRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = SemanticRouter()

    def test_routes_create_song_as_scenario(self) -> None:
        decision = self.router.route_text("session-1", "turn-1", "帮我做一首下班路上听的中文 LoFi")

        self.assertEqual(decision["type"], "route_decision")
        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["scenario_id"], "music_creation")
        self.assertEqual(decision["scenario_intent"], "create_song")
        self.assertEqual(decision["intent"], "create_song")
        self.assertEqual(decision["arguments"]["language"], "zh")
        self.assertEqual(decision["arguments"]["genre"], "lofi")

    def test_routes_revise_song_as_scenario(self) -> None:
        decision = self.router.route_text("session-1", "turn-2", "副歌慢一点")

        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["scenario_id"], "music_creation")
        self.assertEqual(decision["scenario_intent"], "revise_song")

    def test_publish_requires_confirmation(self) -> None:
        decision = self.router.route_text("session-1", "turn-3", "保存并发布")

        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["scenario_intent"], "publish_work")
        self.assertTrue(decision["requires_confirmation"])

    def test_routes_open_page_as_native_action(self) -> None:
        decision = self.router.route_text("session-1", "turn-4", "打开作品页")

        self.assertEqual(decision["mode"], "native_action")
        self.assertEqual(decision["intent"], "open_page")
        self.assertEqual(decision["arguments"], {"target": "work_detail"})

    def test_routes_general_text_as_chat(self) -> None:
        decision = self.router.route_text("session-1", "turn-5", "今天天气怎么样")

        self.assertEqual(decision["mode"], "chat")
        self.assertEqual(decision["intent"], "general")
        self.assertNotIn("scenario_id", decision)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd voice-engine/src
.venv/bin/python -m unittest api.semantic_router.test_router
```

Expected: FAIL because `api.semantic_router` does not exist.

- [ ] **Step 3: Implement models and registry**

Create `models.py` with `Capability` and `RouteInput` dataclasses plus a `RouteDecision` alias:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


RouteMode = Literal["chat", "scenario", "native_action", "server_action", "clarify", "reject"]
RouteDecision = dict[str, Any]


@dataclass(frozen=True)
class RouteInput:
    session_id: str
    turn_id: str
    text: str
    source: str = "manual_text"


@dataclass(frozen=True)
class Capability:
    id: str
    mode: RouteMode
    intent: str
    keywords: tuple[str, ...]
    confidence: float
    scenario_id: str = ""
    scenario_intent: str = ""
    requires_confirmation: bool = False
    arguments: dict[str, Any] = field(default_factory=dict)
```

Create `registry.py` with `default_capabilities()` returning `chat.general`, `music_creation.create_song`, `music_creation.revise_song`, `music_creation.publish_work`, and `native.open_page`.

- [ ] **Step 4: Implement the rule strategy and router facade**

Create `strategies.py` with `RuleBasedStrategy.decide(route_input, capabilities)`. It should normalize text to lowercase, match capabilities by keyword in registry order, return the matched capability, and fall back to `chat.general`.

Create `router.py` with:

```python
from __future__ import annotations

from .models import RouteDecision, RouteInput
from .registry import default_capabilities
from .strategies import RuleBasedStrategy


class SemanticRouter:
    def __init__(self) -> None:
        self.capabilities = default_capabilities()
        self.strategy = RuleBasedStrategy()

    def route_text(self, session_id: str, turn_id: str, text: str, source: str = "manual_text") -> RouteDecision:
        route_input = RouteInput(session_id=session_id, turn_id=turn_id, text=text, source=source)
        return self.strategy.decide(route_input, self.capabilities)
```

Export `SemanticRouter` from `__init__.py`.

- [ ] **Step 5: Run router tests**

Run:

```bash
cd voice-engine/src
.venv/bin/python -m unittest api.semantic_router.test_router
```

Expected: PASS.

## Task 2: CLI And HTTP Text Test Interface

**Files:**
- Create: `voice-engine/src/api/semantic_router/cli.py`
- Modify: `voice-engine/src/api/main.py`
- Test: `voice-engine/src/api/semantic_router/test_router.py`

- [ ] **Step 1: Add failing tests for CLI-friendly JSON and HTTP handler**

Extend `test_router.py` with a test that asserts `json.dumps(decision, ensure_ascii=False)` includes `"type": "route_decision"` and `"mode": "native_action"` for `打开作品页`.

Add a direct async function test for `decide_route` from `api.main`:

```python
import asyncio
from api.main import decide_route


class SemanticRouterHttpTest(unittest.TestCase):
    def test_decide_route_endpoint_returns_decision(self) -> None:
        decision = asyncio.run(decide_route({"text": "保存并发布", "session_id": "debug-session"}))

        self.assertEqual(decision["session_id"], "debug-session")
        self.assertEqual(decision["mode"], "scenario")
        self.assertEqual(decision["scenario_intent"], "publish_work")
        self.assertTrue(decision["requires_confirmation"])
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd voice-engine/src
.venv/bin/python -m unittest api.semantic_router.test_router
```

Expected: FAIL because `decide_route` and CLI do not exist.

- [ ] **Step 3: Implement CLI**

Create `cli.py` that reads text from argv, routes it with `session_id="cli-session"` and `turn_id="turn-1"`, and prints JSON with `ensure_ascii=False`.

- [ ] **Step 4: Add HTTP endpoint**

Modify `main.py`:

```python
from typing import Any
from .semantic_router import SemanticRouter

semantic_router = SemanticRouter()


@app.post("/semantic-router/decide")
async def decide_route(payload: dict[str, Any]):
    text = str(payload.get("text") or "").strip()
    session_id = str(payload.get("session_id") or "debug-session")
    turn_id = str(payload.get("turn_id") or "turn-1")
    return semantic_router.route_text(session_id=session_id, turn_id=turn_id, text=text, source="manual_text")
```

- [ ] **Step 5: Verify tests and CLI**

Run:

```bash
cd voice-engine/src
.venv/bin/python -m unittest api.semantic_router.test_router
.venv/bin/python -m api.semantic_router.cli "打开作品页"
```

Expected: tests PASS; CLI prints JSON with `mode` equal to `native_action`.

## Task 3: Gateway Route Decision Event

**Files:**
- Modify: `voice-engine/src/api/realtime/gateway.py`
- Modify: `voice-engine/src/api/realtime/test_gateway.py`

- [ ] **Step 1: Update failing Gateway test**

Change `test_user_asr_sends_frontend_event_voice_turn_and_transcript_event` to expect:

```python
self.assertEqual(sent_types, ["event", "voice_turn_text", "transcript_event", "route_decision"])
decision = json.loads(client_ws.sent[3])
self.assertEqual(decision["mode"], "scenario")
self.assertEqual(decision["scenario_id"], "music_creation")
self.assertEqual(decision["scenario_intent"], "create_song")
```

- [ ] **Step 2: Run failing Gateway test**

Run:

```bash
cd voice-engine/src
.venv/bin/python -m unittest api.realtime.test_gateway.GatewayDebugLogTest.test_user_asr_sends_frontend_event_voice_turn_and_transcript_event
```

Expected: FAIL because the fourth event is not emitted.

- [ ] **Step 3: Wire Router into Gateway**

Import `SemanticRouter`, initialize `self.semantic_router = SemanticRouter()` in `RealtimeGateway.__init__`, and after `_make_transcript_event(...)` send:

```python
await self._send_json(
    self.semantic_router.route_text(
        session_id=self.session_id,
        turn_id=output_id,
        text=self.current_user_text,
        source="doubao_s2s",
    )
)
```

Update `_record_client_debug()` to record `route_decision` with `mode`, `intent`, `scenario_id`, `scenario_intent`, and `turn_id`.

- [ ] **Step 4: Run Gateway tests**

Run:

```bash
cd voice-engine/src
.venv/bin/python -m unittest api.realtime.test_gateway
```

Expected: PASS.

## Task 4: Frontend Router Test View

**Files:**
- Modify: `voice-engine/src/web/src/app/App.tsx`
- Modify: `voice-engine/src/web/src/app/styles.css`

- [ ] **Step 1: Add TypeScript state and request function**

In `App.tsx`, add `RouteDecision`, `routerText`, `routerResult`, and `routerError` state. Add `testRouter()` that POSTs to `/semantic-router/decide` with `{ text: routerText }`.

- [ ] **Step 2: Add UI section**

Add a `section.router-panel` with an input, "识别意图" button, summary fields, and `<pre>` JSON output. Keep it independent from S2S call state.

- [ ] **Step 3: Style the test view**

In `styles.css`, add `.router-panel`, `.router-form`, `.router-summary`, and `.router-json` styles matching the current quiet operational UI.

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd voice-engine/src/web
npm run build
```

Expected: PASS.

## Task 5: Full Verification And Commit

**Files:**
- All changed files from Tasks 1-4.

- [ ] **Step 1: Run backend tests**

Run:

```bash
cd voice-engine/src
.venv/bin/python -m unittest discover -s . -p 'test*.py'
```

Expected: all tests PASS.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd voice-engine/src/web
npm run build
```

Expected: build exits 0.

- [ ] **Step 3: Check diff**

Run:

```bash
cd /Users/wgxxx/gitee/ECHORURA
git status --short
git diff --stat
```

Expected: only Semantic Router, Gateway integration, frontend test view, and plan files changed.

- [ ] **Step 4: Commit**

Run:

```bash
git add docs/superpowers/plans/2026-06-18-semantic-router.md voice-engine/src/api voice-engine/src/web/src/app
git commit -m "feat: add semantic router text testing"
```

