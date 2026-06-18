# Voice Engine S2S

目标：用 FastAPI + React 直接跑通火山/豆包端到端实时语音 S2S。

## 目录

```text
src/
  api/  FastAPI WebSocket 网关，保存火山凭证并适配 openspeech S2S 二进制协议
  web/  React H5，采集 16k PCM 音频并播放 24k PCM 回复
```

## 配置

复制环境变量模板：

```bash
cp .env.example .env.local
```

填写：

```text
VOLC_API_APP_ID=
VOLC_API_ACCESS_KEY=
```

`VOLC_API_APP_KEY`、`VOLC_API_RESOURCE_ID` 和 `VOLC_WS_URL` 默认使用火山文档值。默认会话已开启唱歌和火山联网搜索，联网搜索还需要填写 `VOLC_WEBSEARCH_API_KEY`。

## 运行

启动 API：

```bash
cd voice-engine/src
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
uvicorn api.main:app --host 127.0.0.1 --port 8787
```

启动 Web：

```bash
cd voice-engine/src/web
npm install
npm run dev
```

打开：

```text
http://127.0.0.1:5173/
```

## P0 验收

- `/health` 返回 `volcConfigured=true`。
- 点击“开始通话”后浏览器请求麦克风权限。
- 页面状态从 `connecting` 变为 `connected`。
- 能看到 ASR 文本、助手文本。
- 能播放火山返回的 24k PCM 音频。
