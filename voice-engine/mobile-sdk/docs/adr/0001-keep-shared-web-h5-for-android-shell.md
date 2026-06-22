# ADR 0001: 保留共享 Web H5 作为 Android 壳子入口

## 状态

Accepted

## 背景

当前已有 `apps/web` 承载实时语音体验。后续计划增加 Android 壳子，但 Android 壳子本身仍调用同一套 Web，而不是重新实现一套移动端前端。

## 决策

保留 `apps/web` 作为共享 Web H5 应用。未来如果新增 Android 原生壳子，放在 `apps/android/`，其职责限定为 WebView 容器、系统权限、设备能力桥接和发布配置。

## 影响

- `apps/web` 内部按 `app/domain/features/components/lib/styles` 分层，承接浏览器和 Android WebView 共用逻辑。
- 不新增 `apps/mobile-h5`，避免同一 Web 被人为拆成两套。
- Android 专属代码不能反向污染 Web 领域目录；需要桥接时应通过清晰的 adapter/interface 接入。
- Node 依赖、Web package 和 Web 构建输出都留在 `apps/web/`，根目录不承载前端工程细节。
