# 平台调用契约

## iframe URL

业务项目嵌入平台页面：

```text
{platformBase}/scenes/{sceneKind}/{sceneId}?embed=1&recordAudio=1&showTranscript=0&saveCallLog=1&consoleTitle=红旗 HS6 用户访谈&requestId={requestId}
```

当前业务固定：

- `sceneKind`: `dialogue`
- `sceneId`: `hs6_user_interview`
- `consoleTitle`: `红旗 HS6 用户访谈`

## postMessage

### 业务项目 -> 平台

启动访谈：

```json
{
  "type": "ai-engine:start",
  "requestId": "req_xxx"
}
```

### 平台 -> 业务项目

平台 ready：

```json
{
  "type": "ai-engine:ready",
  "requestId": "req_xxx",
  "sceneId": "hs6_user_interview"
}
```

平台已开始：

```json
{
  "type": "ai-engine:started",
  "requestId": "req_xxx",
  "sessionId": "session_xxx"
}
```

平台已结束：

```json
{
  "type": "ai-engine:finished",
  "requestId": "req_xxx",
  "sessionId": "session_xxx"
}
```

平台异常：

```json
{
  "type": "ai-engine:error",
  "requestId": "req_xxx",
  "sessionId": "session_xxx",
  "message": "错误信息"
}
```

## 业务 API

创建业务 request：

```text
POST /api/requests
```

```json
{
  "entryParams": {
    "name": "张三",
    "phone": "13800000000",
    "city": "杭州"
  }
}
```

更新业务 request：

```text
PATCH /api/requests/:requestId
```

```json
{
  "platformSessionId": "session_xxx",
  "status": "finished"
}
```

读取业务 request 列表：

```text
GET /api/requests
```

## 平台结果 API

读取聚合结果：

```text
GET /runtime/sessions/:sessionId/result
```

返回核心字段：

```json
{
  "sessionId": "session_xxx",
  "requestId": "req_xxx",
  "sceneId": "hs6_user_interview",
  "status": "finished",
  "transcript": [
    {
      "role": "assistant",
      "text": "您好，我们开始访谈。",
      "at": "10:00:01"
    }
  ],
  "audio": {
    "url": "/runtime/sessions/session_xxx/audio",
    "mime": "audio/wav",
    "source": "client"
  }
}
```

播放录音：

```text
GET /runtime/sessions/:sessionId/audio
```

返回 `audio/wav`，可直接放入：

```tsx
<audio controls src={`${platformApiBase}${audio.url}`} />
```
