# Android SDK + Demo

`apps/android` 现在拆成两层：

- `:sdk`：独立 Android WebView Shell SDK，封装 WebView 容器、麦克风权限桥接、更新检查和宿主配置。
- `:app`：最小 demo 壳，只提供启动配置，继续加载共享 Web H5。

当前 demo 入口仍然是：

```text
https://aivoice.token-gpt.top/
```

这意味着 Android 端继续复用原有能力：

- 共享 Web H5 页面
- Python/FastAPI 实时语音服务
- 现有 `/runtime/intent` 意图识别链路

## 模块说明

| Module | 作用 |
| --- | --- |
| `:sdk` | 给其他 Android 应用复用的宿主层。宿主只需要提供 URL 和少量配置。 |
| `:app` | 当前仓库自带的 demo 壳，用来验证 SDK 能否直接运行到手机。 |

接入说明见：

- [SDK_INTEGRATION.md](SDK_INTEGRATION.md)

## 运行

1. 用 Android Studio 打开 `apps/android/`。
2. 确认使用 JDK 17 或更高版本。
3. 等待 Gradle 同步完成。
4. 选择模拟器或真机运行 `app`。

命令行构建示例：

```bash
JAVA_HOME=<JDK17+> ANDROID_SDK_ROOT=<Android SDK> ./gradlew :sdk:testDebugUnitTest :app:assembleDebug
```

当前调试 APK 输出：

```text
apps/android/app/build/outputs/apk/debug/app-debug.apk
```

Manifest 仍保留明文网络访问配置，方便需要 HTTP 调试或兼容旧资源时使用。

## 后续 SDK 接入方向

目标接入方式是：

1. 宿主 App 依赖 `:sdk` 或后续发布出的 AAR。
2. 宿主提供自己的 `Activity`，继承 SDK 基类。
3. 宿主只配置 `startUrl`、更新清单地址和 bridge 名称。
4. H5 与 Python 服务继续承接实时语音和意图识别。

## 发布到 betaqr/fir.im

先在 betaqr/fir.im 账号里创建 API Token，然后从仓库根目录执行：

```bash
FIR_API_TOKEN=xxx ./scripts/publish-android-betaqr.sh
```

脚本默认构建并上传 debug APK。如果已经有 APK 文件，也可以直接传路径：

```bash
FIR_API_TOKEN=xxx ./scripts/publish-android-betaqr.sh apps/android/app/build/outputs/apk/debug/app-debug.apk
```

发布说明可通过环境变量覆盖：

```bash
BETAQR_CHANGELOG="更新 Android SDK demo 壳" FIR_API_TOKEN=xxx ./scripts/publish-android-betaqr.sh
```

脚本直接调用 betaqr/fir.im 上传 API，不依赖 `fir-cli`。
