# AI Engine Android SDK Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the copied Android shell into an independent `:sdk` module while preserving the original H5, Python service, and intent-recognition behavior for the demo app.

**Architecture:** Keep the existing Web H5 and FastAPI service unchanged, because they already carry realtime voice and `/runtime/intent` behavior. Split the Android project into a reusable `com.android.library` SDK that owns the WebView shell, permission bridge, update check, and host configuration, plus a thin demo app module that supplies app identity and URLs.

**Tech Stack:** Android Gradle modules, Java Activity/WebView code, JUnit 4 unit tests, existing React/Vite H5 app, existing FastAPI runtime intent service

---

## File Structure

- Create: `voice-engine/mobile-sdk/apps/android/sdk/build.gradle`
- Create: `voice-engine/mobile-sdk/apps/android/sdk/src/main/java/com/aiengine/sdk/AiEngineWebShellActivity.java`
- Create: `voice-engine/mobile-sdk/apps/android/sdk/src/main/java/com/aiengine/sdk/AiEngineWebShellConfig.java`
- Create: `voice-engine/mobile-sdk/apps/android/sdk/src/test/java/com/aiengine/sdk/AiEngineWebShellConfigTest.java`
- Modify: `voice-engine/mobile-sdk/apps/android/build.gradle`
- Modify: `voice-engine/mobile-sdk/apps/android/settings.gradle`
- Modify: `voice-engine/mobile-sdk/apps/android/app/build.gradle`
- Modify: `voice-engine/mobile-sdk/apps/android/app/src/main/java/com/aiengine/ai/MainActivity.java`
- Modify: `voice-engine/mobile-sdk/apps/android/README.md`

## Scope Notes

- Preserve the current H5 bridge name `AiEngineAndroid`.
- Preserve the current start URL and update manifest URL for the demo app.
- Keep intent recognition in the Python service untouched; the demo app continues loading the same H5/API chain.
- Do not rename the demo module in this pass; `:app` can remain the runnable sample while `:sdk` becomes independently reusable.
