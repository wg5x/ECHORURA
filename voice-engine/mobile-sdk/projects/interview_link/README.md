# interview_link

`interview_link` 是独立业务小项目，用于“链接进入后填写姓名、电话、城市，并通过平台场景页完成语音访谈”。

它不实现实时语音能力，只调用主平台提供的通用页面和接口：

- 平台页面：`/scenes/:sceneKind/:sceneId`
- 平台 WebSocket：由平台页面内部启动
- 平台结果接口：`/runtime/sessions/:sessionId/result`
- 平台录音接口：`/runtime/sessions/:sessionId/audio`

## 边界

业务项目负责：

- 业务表单：姓名、电话、城市
- 业务 request 列表
- `requestId -> platformSessionId` 绑定
- 访谈详情页中展示业务字段、平台 transcript、平台 audio

平台负责：

- `sceneKind + sceneId` 路由
- `recordAudio / showTranscript / saveCallLog / embed` 等平台参数
- 实时语音会话
- `sessionId`
- transcript 和录音产物

业务字段 `entryParams` 不传给平台，也不由平台理解、校验、注入或保存。

## 运行

需要先启动平台 API 和平台 Web，再启动本项目 API 和 Web。

```bash
# 平台 API
apps/api/.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8790

# 平台 Web
VITE_API_BASE_URL=http://127.0.0.1:8790 npm --prefix apps/web run dev:web -- --port 5176

# 业务 API
apps/api/.venv/bin/python -m uvicorn projects.interview_link.api.main:app --host 127.0.0.1 --port 8788

# 业务 Web
VITE_BUSINESS_API_BASE_URL=http://127.0.0.1:8788 \
VITE_PLATFORM_BASE_URL=http://127.0.0.1:5176 \
VITE_PLATFORM_API_BASE_URL=http://127.0.0.1:8790 \
npm --prefix projects/interview_link/web run dev -- --port 5181
```

打开：

```text
http://127.0.0.1:5181/
```

## 验证

```bash
apps/api/.venv/bin/python -m unittest discover projects/interview_link/api/tests
npm --prefix projects/interview_link/web run build
```

如果本地没有 `projects/interview_link/web/node_modules`，可以临时复用平台 Web 依赖：

```bash
ln -s ../../../apps/web/node_modules projects/interview_link/web/node_modules
```
