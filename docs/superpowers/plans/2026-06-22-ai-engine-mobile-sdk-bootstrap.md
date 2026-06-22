# AI Engine Mobile SDK Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Copy `/Users/wgxxx/gitee/ai-engine` into this repo as an isolated mobile SDK workspace seed without changing runtime behavior in the source repo.

**Architecture:** Keep the copied workspace self-contained under `voice-engine/mobile-sdk/`, preserving the existing `apps/web`, `apps/api`, and `apps/android` layout so the H5, Python service, and Android shell still line up. Limit this pass to safe copy, metadata cleanup, and documentation updates; leave actual Android SDK extraction for the next phase.

**Tech Stack:** Git, shell copy commands, Markdown docs, existing React/Vite web app, FastAPI service, Android Gradle project

---

## File Structure

- Create: `voice-engine/mobile-sdk/`
- Create: `voice-engine/mobile-sdk/README.md`
- Copy into: `voice-engine/mobile-sdk/apps/`
- Copy into: `voice-engine/mobile-sdk/config/`
- Copy into: `voice-engine/mobile-sdk/docs/`
- Copy into: `voice-engine/mobile-sdk/projects/`
- Copy into: `voice-engine/mobile-sdk/scripts/`
- Copy into: `voice-engine/mobile-sdk/package.json`
- Modify: `voice-engine/README.md`

### Task 1: Create the isolated workspace root

**Files:**
- Create: `voice-engine/mobile-sdk/`
- Test: repository tree under `voice-engine/`

- [ ] **Step 1: Create the target directory**

Run:

```bash
mkdir -p /Users/wgxxx/gitee/ECHORURA/voice-engine/mobile-sdk
```

- [ ] **Step 2: Verify the directory exists**

Run:

```bash
find /Users/wgxxx/gitee/ECHORURA/voice-engine -maxdepth 2 -type d | sort
```

Expected: includes `/Users/wgxxx/gitee/ECHORURA/voice-engine/mobile-sdk`

### Task 2: Copy the source workspace without git or cache baggage

**Files:**
- Create: `voice-engine/mobile-sdk/README.md`
- Create: `voice-engine/mobile-sdk/package.json`
- Create: `voice-engine/mobile-sdk/apps/**`
- Create: `voice-engine/mobile-sdk/config/**`
- Create: `voice-engine/mobile-sdk/docs/**`
- Create: `voice-engine/mobile-sdk/projects/**`
- Create: `voice-engine/mobile-sdk/scripts/**`
- Test: copied tree contents

- [ ] **Step 1: Copy the tracked workspace shape**

Run:

```bash
rsync -a \
  --exclude '.git' \
  --exclude '.DS_Store' \
  --exclude '.playwright-cli' \
  --exclude '.pytest_cache' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude 'build' \
  --exclude 'dist' \
  /Users/wgxxx/gitee/ai-engine/ \
  /Users/wgxxx/gitee/ECHORURA/voice-engine/mobile-sdk/
```

- [ ] **Step 2: Verify the copied root is self-contained**

Run:

```bash
find /Users/wgxxx/gitee/ECHORURA/voice-engine/mobile-sdk -maxdepth 2 -type d | sort
```

Expected: includes `apps`, `config`, `docs`, `projects`, and `scripts`

### Task 3: Rewrite the copied README for its new role

**Files:**
- Modify: `voice-engine/mobile-sdk/README.md`
- Test: rendered README text

- [ ] **Step 1: Replace the source-project framing with mobile-sdk framing**

Write a README that states:

```markdown
# mobile-sdk workspace

这个目录是从 `/Users/wgxxx/gitee/ai-engine` 复制出来的工作副本，用于在 ECHORURA 仓库内演进 Android SDK 化方案。

当前阶段目标：

- 保留共享 Web H5、Python 服务、Android 壳的原始协作关系
- 不回写源 `ai-engine` 仓库
- 为后续 `apps/android/sdk + demo` 拆分提供安全改造空间
```

- [ ] **Step 2: Verify the README references the copied-workspace purpose**

Run:

```bash
sed -n '1,160p' /Users/wgxxx/gitee/ECHORURA/voice-engine/mobile-sdk/README.md
```

Expected: mentions copied workspace, ECHORURA, and upcoming SDK extraction

### Task 4: Link the new workspace from the parent Voice Engine docs

**Files:**
- Modify: `voice-engine/README.md`
- Test: parent README excerpt

- [ ] **Step 1: Add one concise entry for `mobile-sdk/`**

Update the README so it includes a line like:

```markdown
- [mobile-sdk 工作副本](mobile-sdk/README.md)：从 `ai-engine` 复制出的 Android/Web/Python 联调工作副本，用于后续 SDK 化拆分。
```

- [ ] **Step 2: Verify the parent README mentions the new directory**

Run:

```bash
rg -n "mobile-sdk" /Users/wgxxx/gitee/ECHORURA/voice-engine/README.md
```

Expected: one hit describing the copied workspace

### Task 5: Run minimal verification and capture the next SDK extraction seam

**Files:**
- Test: `voice-engine/mobile-sdk/apps/android/app/src/main/java/com/aiengine/ai/MainActivity.java`
- Test: git working tree

- [ ] **Step 1: Verify the copied Android shell entry still exists**

Run:

```bash
test -f /Users/wgxxx/gitee/ECHORURA/voice-engine/mobile-sdk/apps/android/app/src/main/java/com/aiengine/ai/MainActivity.java
```

Expected: exit code `0`

- [ ] **Step 2: Verify the copied web package manifest still exists**

Run:

```bash
test -f /Users/wgxxx/gitee/ECHORURA/voice-engine/mobile-sdk/apps/web/package.json
```

Expected: exit code `0`

- [ ] **Step 3: Inspect the final diff**

Run:

```bash
git -C /Users/wgxxx/gitee/ECHORURA status --short
```

Expected: only new `voice-engine/mobile-sdk/**` files and the intentional `voice-engine/README.md` change
