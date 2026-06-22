# mobile-sdk workspace

这个目录是从 `/Users/wgxxx/gitee/ai-engine` 复制出来的工作副本，用于在 ECHORURA 仓库内演进 Android SDK 化方案。

当前阶段目标：

- 保留共享 Web H5、Python 服务、Android 壳的原始协作关系
- 不回写源 `ai-engine` 仓库
- 已经完成 `apps/android/:sdk + :app` 拆分，Android SDK 可独立构建为 AAR

## 当前结构

| 路径 | 作用 |
| --- | --- |
| `apps/web/` | 共享 Web H5，继续承载浏览器和 Android WebView 共用界面。 |
| `apps/api/` | Python/FastAPI 服务，继续提供实时语音网关、运行时接口和 `/runtime/intent` 意图识别。 |
| `apps/android/` | Android SDK 与 demo 工作区，包含 `:sdk` Android library module 和 `:app` demo module。 |
| `config/` | 环境变量和 TypeScript 配置模板。 |
| `docs/` | 从源仓库复制的产品、架构、ADR 与参考资料。 |
| `projects/` | 源仓库里的附属项目，暂时原样保留。 |
| `scripts/` | Web/API/Android 相关脚本，包含 Android emulator smoke 检查。 |

## 本阶段边界

这一次已经完成：

1. 在当前仓库里落一个和源项目隔离的工作副本。
2. 保持 Web H5 和 Python API 与源项目一致。
3. 把 Android 壳抽成独立 `:sdk` module，demo `:app` 只保留最小启动配置。
4. 保留服务端意图识别链路，SDK 通过同一套 H5 + Python 服务复用它。

这一次不做：

- 改 Web 或 Python 业务逻辑
- 调整运行协议
- 把意图识别下沉到 Android 本地

## Android SDK

Android 目录说明：

- `apps/android/sdk/`：可复用 SDK，封装 WebView、麦克风权限桥接、更新检查和宿主配置。
- `apps/android/app/`：demo 壳，继承 SDK Activity 并配置当前线上 H5 URL。
- `apps/android/SDK_INTEGRATION.md`：其他 Android 应用的接入说明。

构建 SDK 和 demo：

```bash
cd apps/android
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" \
ANDROID_SDK_ROOT="$HOME/Library/Android/sdk" \
./gradlew :sdk:testDebugUnitTest :sdk:assembleDebug :app:assembleDebug
```

输出产物：

```text
apps/android/sdk/build/outputs/aar/sdk-debug.aar
apps/android/app/build/outputs/apk/debug/app-debug.apk
```

## 验证命令

服务端意图识别测试：

```bash
PYTHONPATH=/Users/wgxxx/gitee/ECHORURA/voice-engine/mobile-sdk \
python3 -m unittest apps/api/tests/test_intent_service.py
```

Android emulator smoke：

```bash
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" \
scripts/android-emulator-smoke.sh
```
