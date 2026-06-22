# interview_link 实现计划

## 目标

在 `projects/interview_link` 中实现一个独立业务项目。它保存业务字段和 request 列表，通过 iframe 调用平台场景页，通过 `sessionId` 读取平台 transcript 和录音。

## 架构

- `projects/interview_link/api`：业务 API，保存 `entryParams`、`requestId`、`platformSessionId`。
- `projects/interview_link/web`：业务前端，展示表单、iframe、访谈列表、访谈详情。
- `apps/web`：平台通用页面，支持嵌入模式和平台参数。
- `apps/api`：平台通用 API，支持按 `sessionId` 读取结果和 WAV 录音。

## 实施项

### 平台侧

- 增加 `/runtime/sessions/:sessionId/result`。
- 增加 `/runtime/sessions/:sessionId/audio`。
- call log 保存 `sessionId` 和 `requestId`。
- 录音 manifest 保存 `sessionId` 和 `requestId`。
- WebSocket start 支持 `requestId` 和 `recordAudio`。
- 平台页支持 `embed / recordAudio / showTranscript / saveCallLog / requestId` 查询参数。
- 平台页通过 `postMessage` 返回 `ready / started / finished / error`。
- 平台不再解析或注入业务 `entryParams`。

### 业务侧

- 创建业务 request。
- 保存姓名、电话、城市。
- 保存 `requestId -> platformSessionId` 绑定。
- iframe 打开平台场景页。
- 点击业务列表可查看详情。
- 详情页展示平台 transcript。
- 详情页使用平台 audio URL 直接播放录音。

## 验证命令

```bash
apps/api/.venv/bin/python -m unittest discover projects/interview_link/api/tests
npm --prefix projects/interview_link/web run build
apps/api/.venv/bin/python -m unittest discover apps/api/tests
npm --prefix apps/web run build
node --test apps/web/src/domain/scene/sceneRoutes.test.mjs
```
