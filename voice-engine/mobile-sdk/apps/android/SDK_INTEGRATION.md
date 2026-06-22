# Android SDK Integration

本文档说明其他 Android 应用如何复用 `apps/android/:sdk`。

当前这套 SDK 的定位很明确：

- Android 侧只提供 WebView 壳、麦克风权限桥接、更新检查和宿主配置
- 共享 Web H5 继续承载主要交互界面
- Python/FastAPI 服务继续承载实时语音和意图识别

也就是说，宿主 App 接入的是：

```text
Host Android App
  -> ai-engine Android SDK
    -> Shared Web H5
      -> Python realtime / runtime service
        -> intent recognition
```

## 1. 依赖方式

当前仓库内有两种接入方式：

### 方式 A：源码 module 依赖

如果宿主 App 和本仓库在同一个 Android 工程中，直接依赖 `:sdk`：

```gradle
dependencies {
    implementation project(":sdk")
}
```

### 方式 B：AAR 依赖

当前可构建产物：

```text
apps/android/sdk/build/outputs/aar/sdk-debug.aar
```

宿主 App 可以先以本地 AAR 的形式集成，后续再决定是否发布到 Maven 仓库。

## 2. 宿主 Activity 写法

宿主只需要继承 SDK 基类，并提供一份配置：

```java
package com.example.hostapp;

import com.aiengine.sdk.AiEngineWebShellActivity;
import com.aiengine.sdk.AiEngineWebShellConfig;

public class HostVoiceActivity extends AiEngineWebShellActivity {
    @Override
    protected AiEngineWebShellConfig createWebShellConfig() {
        return new AiEngineWebShellConfig.Builder("https://aivoice.token-gpt.top/")
                .setUpdateManifestUrl("https://aivoice.token-gpt.top/android-version.json")
                .setDefaultUpdateUrl("https://www.betaqr.com.cn/bka92l6c")
                .setUpdateCheckEnabled(true)
                .build();
    }
}
```

当前 SDK 默认 bridge 名称是：

```text
AiEngineAndroid
```

如果宿主 H5 侧使用的是当前复制过来的 Web，应保持这个名字不变。

## 3. 宿主 Manifest 要求

至少需要下面这些权限：

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

如果宿主需要直接复用当前 demo 的网络策略，也需要：

```xml
<application
    android:usesCleartextTraffic="true" />
```

## 4. 服务依赖

SDK 不是离线语音引擎。

它依赖现有服务链路：

- Web H5 页面地址
- Python/FastAPI `/realtime`
- Python/FastAPI `/runtime/*`
- Python/FastAPI `/runtime/intent`

因此“意图识别”仍然来自服务端，而不是 Android SDK 本地实现。

当前服务端意图识别逻辑位置：

```text
apps/api/runtime/intent_service.py
```

当前客户端调用入口：

```text
apps/web/src/lib/runtimeApi.ts
```

## 5. 当前已验证内容

当前仓库内已经验证：

1. `:sdk:testDebugUnitTest` 可通过
2. `:sdk:assembleDebug` 可产出 AAR
3. `:app:assembleDebug` 可产出 APK
4. APK 已在 Android 模拟器中安装并启动
5. WebView 可加载共享 H5 首页和场景页
6. Python 意图识别测试可通过

## 6. 下一步建议

如果要让其他 Android 应用接入更快，建议下一步继续做这几件事：

1. 把 `sdk-debug.aar` 升级为正式发布产物
2. 为 SDK 增加可扩展的 Native Action bridge
3. 给宿主暴露更新开关、日志开关和 WebView 调试开关
4. 增加真机安装与麦克风授权回归检查
