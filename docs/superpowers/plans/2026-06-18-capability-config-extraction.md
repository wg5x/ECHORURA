# Capability Config Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Semantic Router capability definitions out of `semantic_router/registry.py` into an independent backend config module.

**Architecture:** Add `api.configs.capability_config` as the data-only source for capability definitions. Keep `semantic_router.registry` as a thin adapter that converts config objects into Router `Capability` models, preserving all current route behavior.

**Tech Stack:** Python 3.11, unittest.

---

## File Map

- Create `voice-engine/src/api/configs/__init__.py`: config package marker.
- Create `voice-engine/src/api/configs/capability_config.py`: capability config dataclass and defaults.
- Create `voice-engine/src/api/configs/test_capability_config.py`: data completeness tests.
- Modify `voice-engine/src/api/semantic_router/registry.py`: consume config module instead of defining data inline.

## Task 1: Extract Capability Config

**Files:**
- Create: `voice-engine/src/api/configs/__init__.py`
- Create: `voice-engine/src/api/configs/capability_config.py`
- Create: `voice-engine/src/api/configs/test_capability_config.py`
- Modify: `voice-engine/src/api/semantic_router/registry.py`

- [ ] **Step 1: Write failing config test**

Create `test_capability_config.py` asserting `default_capability_configs()` contains `music_creation.create_song`, `native.open_page`, and `chat.general`, and that IDs are unique.

- [ ] **Step 2: Run failing test**

Run: `cd voice-engine/src && .venv/bin/python -m unittest api.configs.test_capability_config`

Expected: FAIL because `api.configs.capability_config` does not exist.

- [ ] **Step 3: Add config dataclass and defaults**

Create `capability_config.py` with a frozen `CapabilityConfig` dataclass and the existing capability values copied from `semantic_router/registry.py`.

- [ ] **Step 4: Adapt registry**

Change `semantic_router/registry.py` so `default_capabilities()` maps `CapabilityConfig` records into `Capability`.

- [ ] **Step 5: Verify behavior**

Run:

```bash
cd voice-engine/src
.venv/bin/python -m unittest api.configs.test_capability_config api.semantic_router.test_router
```

Expected: PASS.

## Task 2: Full Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd voice-engine/src && .venv/bin/python -m unittest discover -s . -p 'test*.py'`

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run: `cd voice-engine/src/web && npm run build`

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
git add docs/superpowers/plans/2026-06-18-capability-config-extraction.md voice-engine/src/api/configs voice-engine/src/api/semantic_router/registry.py
git commit -m "refactor: extract capability config"
```

