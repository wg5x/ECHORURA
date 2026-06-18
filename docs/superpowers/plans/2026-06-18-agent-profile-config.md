# Agent Profile Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend Agent Profile configuration with exactly two initial profiles: `default` and `phone-assistant`.

**Architecture:** Add `api.configs.agent_profile_config` as a data-only module. It references existing Voice Profile IDs and Capability IDs, but does not wire Agent Profiles into Router yet.

**Tech Stack:** Python 3.11, unittest.

---

## File Map

- Create `voice-engine/src/api/configs/agent_profile_config.py`: agent profile dataclass and defaults.
- Create `voice-engine/src/api/configs/test_agent_profile_config.py`: uniqueness and reference-integrity tests.
- Modify `voice-engine/src/api/configs/voice_profile_config.py`: rename the backend default voice profile ID to `default`.
- Modify `voice-engine/src/api/configs/test_voice_profile_config.py`: expect `default`.

## Task 1: Add Agent Profile Config

- [ ] Write failing tests for exactly `default` and `phone-assistant`.
- [ ] Verify tests fail because `agent_profile_config` does not exist.
- [ ] Add `AgentProfileConfig` and `default_agent_profile_configs()`.
- [ ] Update backend default Voice Profile ID to `default`.
- [ ] Run config tests and full verification.
