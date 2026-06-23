# Native Bridge

SDK 默认向 WebView 注入的 bridge 名称是：

```text
AiEngineAndroid
```

宿主可以通过 `AiEngineWebShellConfig.Builder#setBridgeName` 改名；如果继续使用当前复制出的 H5，建议保持默认值。

## H5 可调用方法

```ts
window.AiEngineAndroid?.hasMicrophonePermission(): boolean
window.AiEngineAndroid?.requestMicrophonePermission(): void
window.AiEngineAndroid?.openAppSettings(): void
window.AiEngineAndroid?.openSystemSettings(target: string): void
window.AiEngineAndroid?.openUrl(url: string): void
window.AiEngineAndroid?.openIntent(action: string, dataUri: string, mimeType: string): void
window.AiEngineAndroid?.shareText(title: string, text: string, url: string): void
window.AiEngineAndroid?.chooseFile(requestId: string, acceptTypes: string, allowMultiple: boolean): void
```

`openSystemSettings` 当前支持这些 `target`：

```text
app
wifi
bluetooth
accessibility
notification
settings
```

`chooseFile` 支持 MIME 类型列表，例如：

```ts
window.AiEngineAndroid?.chooseFile("audio-1", "audio/*", false);
window.AiEngineAndroid?.chooseFile("docs-1", "text/plain,application/pdf", true);
```

这可以用于录音文件、播客素材、文档等本地文件选择。SDK 回传的是 Android `content://` URI 和文件元数据；如果后续要上传文件内容，建议继续在 Native 侧加上传方法，避免 H5 直接处理 Android 私有 URI。

标准 WebView `<input type="file">` 也已经接入 Android 文件选择器，不需要额外 JS bridge。

## H5 监听事件

麦克风权限结果：

```ts
window.addEventListener("ai-engine-android-microphone-permission", (event) => {
  const detail = (event as CustomEvent<{ granted: boolean }>).detail;
});
```

Native 动作结果：

```ts
window.addEventListener("ai-engine-android-native-result", (event) => {
  const detail = (event as CustomEvent<{
    action: string;
    success: boolean;
    message: string;
  }>).detail;
});
```

文件选择结果：

```ts
window.addEventListener("ai-engine-android-file-selection", (event) => {
  const detail = (event as CustomEvent<{
    requestId: string;
    cancelled: boolean;
    error: string;
    files: Array<{
      uri: string;
      name: string;
      mimeType: string;
      size: number;
    }>;
  }>).detail;
});
```

## 安全边界

- Bridge 默认只在宿主配置的 H5 中使用；不要把不可信网页直接接到同一个 bridge。
- `openIntent` 会按 H5 传入的 action/data/type 打开系统 Intent，宿主如果要限制范围，应在自己的 SDK fork 或后续策略层里收窄。
- 文件选择只返回 URI 和元数据，不自动读取或上传文件内容。
