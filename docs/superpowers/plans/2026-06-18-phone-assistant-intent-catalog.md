# Phone Assistant Intent Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first Android-style phone intent catalog to `phone-assistant` and make Semantic Router decisions respect `agent_profile_id`.

**Architecture:** Keep Android execution out of this change. Backend capability config owns `native.*` intents; Agent Profile owns which capabilities are enabled; Semantic Router filters capabilities by agent before rule matching and returns structured `route_decision` arguments for text testing.

**Tech Stack:** Python dataclasses, `unittest`, FastAPI endpoint, React/Vite frontend.

---

### Task 1: Agent-Scoped Router

**Files:**
- Modify: `voice-engine/src/api/semantic_router/router.py`
- Modify: `voice-engine/src/api/semantic_router/registry.py`
- Modify: `voice-engine/src/api/main.py`
- Test: `voice-engine/src/api/semantic_router/test_router.py`

- [x] Write tests proving `phone-assistant` rejects music-only intent and returns `agent_profile_id`.
- [x] Run the router tests and confirm they fail because `route_text()` does not accept `agent_profile_id`.
- [x] Implement capability filtering from `AgentProfileConfig.enabled_capability_ids`.
- [x] Pass `agent_profile_id` through `/semantic-router/decide`.
- [x] Run router tests and confirm they pass.

### Task 2: First Phone Intent Catalog

**Files:**
- Modify: `voice-engine/src/api/configs/capability_config.py`
- Modify: `voice-engine/src/api/configs/agent_profile_config.py`
- Modify: `voice-engine/src/api/semantic_router/strategies.py`
- Test: `voice-engine/src/api/configs/test_agent_profile_config.py`
- Test: `voice-engine/src/api/semantic_router/test_router.py`

- [x] Write tests for these texts under `phone-assistant`: `打开淘宝`, `看视频`, `打开相册选一张图片`, `打开 Wi-Fi 设置`, `今天下午三点开会`, `打电话 13641194007`, `发短信`.
- [x] Run the focused tests and confirm they fail because capabilities and extractors are missing.
- [x] Add minimal `native.*` capabilities with keyword matching and static Android intent hints.
- [x] Add extractors for app name, phone number, calendar title/time text, URL, media type, and gallery media type.
- [x] Run focused tests and confirm they pass.

### Task 3: Frontend Text Test Agent Selector

**Files:**
- Modify: `voice-engine/src/web/src/app/App.tsx`

- [x] Send `agent_profile_id` from the Semantic Router test panel.
- [x] Surface `agent_profile_id` in the JSON result.
- [x] Run `npm run build`.

### Verification

- [x] `cd voice-engine/src && .venv/bin/python -m unittest discover -s . -p 'test*.py'`
- [x] `cd voice-engine/src/web && npm run build`
- [x] `git grep -n -i echorura -- voice-engine/src` returns no matches.
