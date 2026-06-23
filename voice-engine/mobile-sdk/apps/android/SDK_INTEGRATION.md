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

当前仓库内有三种接入方式：

### 方式 A：源码 module 依赖

如果宿主 App 和本仓库在同一个 Android 工程中，直接依赖 `:sdk`：

```gradle
dependencies {
    implementation project(":sdk")
}
```

### 方式 B：本地 Maven 依赖

构建并发布 release SDK 到本工程内的本地 Maven 仓库：

```bash
cd apps/android
./gradlew :sdk:publishReleasePublicationToLocalSdkRepository
```

产物坐标：

```text
com.aiengine:ai-engine-android-sdk:0.2.0
```

仓库位置：

```text
apps/android/sdk/build/local-maven
```

宿主工程示例：

```gradle
repositories {
    maven {
        url uri("/path/to/ECHORURA/voice-engine/mobile-sdk/apps/android/sdk/build/local-maven")
    }
}

dependencies {
    implementation "com.aiengine:ai-engine-android-sdk:0.2.0"
}
```

### 方式 C：AAR 文件依赖

当前可构建产物：

```text
apps/android/sdk/build/outputs/aar/sdk-release.aar
```

宿主 App 也可以先以本地 AAR 的形式集成。

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

最小宿主示例：

```text
apps/android/samples/host-app/
```

构建命令：

```bash
cd apps/android
./gradlew :samples:host-app:assembleDebug
```

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

## 5. Native Bridge

SDK 现在额外封装了常用宿主能力：

- 分享文本和链接
- 打开 URL
- 打开 App/Wi-Fi/蓝牙/通知/无障碍/系统设置页
- 按 action/data/type 打开 Android Intent
- 通过 bridge 选择文件并回传 `content://` URI 和元数据
- 支持标准 WebView `<input type="file">`

详细协议见：

```text
apps/android/NATIVE_BRIDGE.md
```

## 6. 当前已验证内容

当前仓库内已经验证：

1. `:sdk:testDebugUnitTest` 可通过
2. `:sdk:assembleRelease` 可产出 release AAR
3. `:sdk:publishReleasePublicationToLocalSdkRepository` 可发布本地 Maven 产物
4. `:samples:host-app:assembleDebug` 可构建最小宿主示例
5. `:app:assembleDebug` 可产出 demo APK
6. APK 已在 Android 模拟器中安装并启动
7. WebView 可加载共享 H5 首页和场景页
8. Python 意图识别测试可通过
