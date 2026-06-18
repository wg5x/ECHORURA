# Voice Profile Config Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move backend Voice Profile defaults and speaker allowlists out of Volc payload construction into a standalone config module.

**Architecture:** Add `api.configs.voice_profile_config` as the backend data source for voice profile defaults and speaker allowlists. Keep `integrations.volc.payload` responsible only for normalizing input and building Volc StartSession payloads.

**Tech Stack:** Python 3.11, unittest.

---

## File Map

- Create `voice-engine/src/api/configs/voice_profile_config.py`: voice profile dataclass, default profiles, speaker constants, allowlists.
- Create `voice-engine/src/api/configs/test_voice_profile_config.py`: data completeness and uniqueness tests.
- Modify `voice-engine/src/api/integrations/volc/payload.py`: import defaults and allowlists from config.

## Task 1: Extract Voice Profile Config

- [ ] Write failing tests for default profiles, default speaker IDs, and profile ID uniqueness.
- [ ] Run `cd voice-engine/src && .venv/bin/python -m unittest api.configs.test_voice_profile_config` and verify it fails because the module does not exist.
- [ ] Add `voice_profile_config.py` with `VoiceProfileConfig`, `DEFAULT_O2_SPEAKER`, `DEFAULT_SC2_SPEAKER`, `O2_SPEAKERS`, `SC2_SPEAKERS`, `default_voice_profile_configs()`, and `default_realtime_config()`.
- [ ] Update `integrations/volc/payload.py` to import those values instead of defining them inline.
- [ ] Run `cd voice-engine/src && .venv/bin/python -m unittest api.configs.test_voice_profile_config api.integrations.volc.test_payload`.

## Task 2: Full Verification

- [ ] Run `cd voice-engine/src && .venv/bin/python -m unittest discover -s . -p 'test*.py'`.
- [ ] Run `cd voice-engine/src/web && npm run build`.
- [ ] Commit with `git commit -m "refactor: extract voice profile config"`.

