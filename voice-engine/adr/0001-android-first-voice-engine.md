# ADR-0001：Voice Engine 采用 H5-first + Native Shell 主路径

日期：2026-06-14

## 状态

Accepted

## 背景

ECHORURA 当前产品方向是“语音优先的 AI 音乐创作工具”，第一目标用户包含视觉障碍者和低操作门槛创作者。用户会在自己的手机上完成创作、试听、修改、保存和发布。

同时，业务页面需要尽量复用到 PC Web 和 Android WebView，避免 Android 原生和 Web 两套业务逻辑分叉。

早期架构讨论中提到过 `mobile-use` 云手机自动化。但云手机意味着：

- 需要绑定和隔离每个用户的远程手机实例。
- 需要处理第三方 App 登录态。
- 会引入账号、隐私、合规和成本复杂度。
- 不适合作为用户自己手机上的音乐创作主路径。

Android 本身已经提供 Intent、Deep Link、Activity Result、Service、WorkManager 等机制。对 ECHORURA 来说，端侧动作应优先由用户自己的 Android App 执行，但核心业务页面应由 H5 承载，通过 Android WebView + Native Shell 获得系统能力。

## 决策

Voice Engine 主路径采用 H5-first + Native Shell：

- 核心业务页面使用 H5，实现 Android WebView 和 PC Web 复用。
- Android 是第一阶段 Native Shell，负责麦克风权限、语音能力、Intent、分享、文件选择、通知和无障碍增强。
- H5 通过 JS Bridge 调用 Native 白名单能力。
- 服务端负责语义路由、场景任务编排、业务事件记录和流式反馈。
- 云手机只作为远程兜底能力，不进入 MVP 主路径。

## 后果

正面影响：

- 用户使用自己的账号、权限和设备，降低登录态和隐私复杂度。
- H5 页面可被 PC 和 Android WebView 复用，减少业务实现重复。
- 能更好服务视觉障碍用户的端侧无障碍体验。
- 可以复用 Android 系统能力，例如分享、文件选择、浏览器、设置页、通知。
- 架构更贴近可扩展的语音业务工作台，而不是单一音乐 App 或通用远程自动化工具。

限制：

- Android Intent 不能任意控制第三方 App 内部 UI。
- H5 与 Native Bridge 需要定义稳定协议。
- PC Web 没有 Android Intent 能力，需要浏览器降级方案或隐藏相关动作。
- 需要端侧维护 action 白名单和权限处理。
- 需要针对 Android 版本差异处理 package visibility、后台启动限制、通知权限等。

## 修正

早期文档称为 Android-first，容易误解为所有业务都要 Android 原生实现。本文修正为 H5-first + Native Shell：Android 仍然是首个落地壳，但业务页面优先 H5 化。

## 不采用的方案

### 云手机主路径

不采用。它适合远程自动化和代执行，不适合作为用户本机语音音乐创作的默认链路。

### 纯服务端语音助手

不采用。它无法充分利用端侧账号、权限、无障碍和本地交互能力。
