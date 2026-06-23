# Minimal Host App

这个 sample 模拟其他 Android 应用接入 AI Engine SDK。

它只做三件事：

1. 依赖 `:sdk`
2. 声明宿主 Manifest 权限
3. 提供一个继承 `AiEngineWebShellActivity` 的 `HostVoiceActivity`

运行：

```bash
cd apps/android
./gradlew :samples:host-app:assembleDebug
```

入口代码：

```text
samples/host-app/src/main/java/com/example/aienginehost/HostVoiceActivity.java
```
