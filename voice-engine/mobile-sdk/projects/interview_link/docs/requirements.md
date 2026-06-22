# interview_link 需求说明

## 背景

平台已经具备按 `sceneKind + sceneId` 打开场景并完成实时语音会话的能力。本需求要在 `projects` 目录下创建独立业务项目，提供一个面向访谈链接的业务页面。

该项目不是平台本身的一部分。它只调用平台提供的通用页面和接口。

## 目标

用户打开业务页面后，可以：

1. 填写姓名、电话、城市。
2. 创建一次业务访谈请求，生成 `requestId`。
3. 在页面中通过 iframe 打开平台场景页。
4. 平台开始语音访谈后返回 `sessionId`。
5. 业务项目保存 `requestId -> sessionId` 的绑定关系。
6. 访谈完成后，业务项目可以查看该次访谈的对话内容和可直接播放的录音。

## 非目标

- 不把姓名、电话、城市传给平台。
- 不让平台理解业务字段。
- 不在平台里实现业务表单。
- 不在平台里维护业务 request 列表。
- 不做后台监控人数、进度预警。
- 不做问卷选择、语音类型选择等业务外选项。

## 平台参数

业务页面通过 iframe URL 给平台传平台参数：

```text
/scenes/dialogue/hs6_user_interview?embed=1&recordAudio=1&showTranscript=0&saveCallLog=1&consoleTitle=红旗 HS6 用户访谈&requestId=req_xxx
```

参数含义：

- `embed=1`：平台进入嵌入模式。
- `recordAudio=1`：平台本次会话保存录音。
- `showTranscript=0`：平台访谈中不展示字幕/对话列表。
- `saveCallLog=1`：平台会话结束后保存转写日志。
- `consoleTitle=红旗 HS6 用户访谈`：平台嵌入页顶部标题。
- `requestId=req_xxx`：业务请求 ID，只作为外部关联 ID。

## 业务数据

业务 request 示例：

```json
{
  "requestId": "req_20260618154813011065_b96ade",
  "sceneKind": "dialogue",
  "sceneId": "hs6_user_interview",
  "entryParams": {
    "name": "张三",
    "phone": "13800000000",
    "city": "杭州"
  },
  "platformSessionId": "session_xxx",
  "status": "finished"
}
```

`entryParams` 只属于业务项目。

## 结果展示

业务详情页通过平台 `sessionId` 读取：

- `transcript`：渲染为对话列表。
- `audio.url`：用于 `<audio controls>` 直接播放录音。

平台聚合接口：

```text
GET /runtime/sessions/:sessionId/result
```

平台音频接口：

```text
GET /runtime/sessions/:sessionId/audio
GET /runtime/sessions/:sessionId/audio?source=assistant
```
