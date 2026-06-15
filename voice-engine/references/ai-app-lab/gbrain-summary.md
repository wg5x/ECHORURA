---
title: AI App Lab（火山方舟豆包）技术地图·摘要
type: note
tags: [火山方舟, 豆包, Arkitect, Agent, 语音, ai-app-lab]
---

# AI App Lab 技术地图（摘要版）

火山引擎·火山方舟（豆包大模型）官方 AI 应用实验室。把豆包大模型落地成可运行场景应用的"积木库"。仓库：volcengine/ai-app-lab。完整文档见仓库 `docs/AI-App-Lab-技术地图.md`。

## 四大组成
- **arkitect/** — 官方高代码 Python SDK（`pip install arkitect`，Apache 2.0）。
- **demohouse/** — 26 个垂直场景原型应用（自用许可）。
- **mcp/server/** — 7 个官方 MCP 工具服务。
- **examples/** — SDK 入门示例。

## Arkitect SDK 核心组件
LLM 调用 / Agent 框架（`BaseAgent` 支持 tools、sub_agents、Hooks、Runner）/ ASR 流式识别 / TTS 流式合成 / Tool+MCP Client / Context+Prompt / Telemetry Trace / Checkpoint。
启动：`launch_serve()` 本地，或 veFaaS 部署。

## Demohouse 关键 Demo（按场景）
- **语音/实时**：live_voice_call（WebSocket 级联，效果一般）；rtc_conversational_ai⭐（RTC 全双工+VAD打断+~1s延迟，支持 CustomLLM，源码在外部 rtc-aigc-demo）；conversational_ai_embedded（ESP32 硬件）；video_analyser（视频+语音）。
- **Agent/行动派**：mobile-use⭐（云手机+豆包视觉+LangGraph ReAct，操作以 MCP 工具暴露）；computer_use（桌面 UI-TARS）；vefaas-browser-use（浏览器）；deep_search_mcp（Supervisor→Worker 多 Agent）；ad_video_gen（A2A 四 Agent）；game_agent_ai。
- **内容生成**：chat2cartoon(_en)、storybook-agent、video_gen_demo、media2doc。
- **检索/知识/推理**：deep_search(_en)、deepdoubao、longterm_memory（mem0+VikingDB）、animal_recognition、quant_trading。
- **多模态/移动端**：multimodalkit_example⭐（Android/iOS/Web 多模态 SDK：ASR/TTS/端侧分割/识物/实时通话）；pocket_pal（悬浮球所见即所说，仅开源 Web）；teacher_avatar；snap_shop。
- **电商客服**：shop_assist（FC+RAG）。

## MCP Server（工具生态）
mcp_server_ark（方舟Bot/联网/链接解析）、vefaas_browser_use、knowledgebase、ppt、vefaas_function、vefaas_sandbox、tls。手机操作的 mcp_server_mobile_use 在外部仓库 volcengine/mcp-server。

## 实时语音三方案对比（关键结论）
| 方案 | 特点 | 自定义大脑/多Agent |
|---|---|---|
| live_voice_call | 级联、半双工、不可打断、延迟高 | 要自己拼 |
| RTC+CustomLLM ⭐ | 全双工/VAD打断/降噪/~1s | ✅ CustomLLM 回调你的 Agent 网关 |
| 端到端 S2S | 最拟人、最低延迟 | 较弱（黑盒，靠 function calling）|
结论：做"语音入口+语义路由+多 Agent"，首选 **RTC 对话式 AI + CustomLLM**，大脑用 Arkitect 自建。

## 推荐落地架构
用户语音 →(RTC: ASR/VAD/降噪/TTS)→ CustomLLM 回调 → Arkitect Agent 网关（语义路由）→ 分发到 客服/知识/mobile-use操作手机/陪伴 等业务 Agent → 工具/数据/API。需要操作手机的任务把 mobile-use 当工具/子 Agent 挂上。

## 商机方向
行业语音客服（最易变现）/ 拟人陪伴（+长期记忆）/ 语音控制行动派 Agent（差异化最强，接 mobile-use|computer_use）/ 垂直语音助理（教育/导购/车载）/ 企业知识语音问答台。

## 凭证清单
通用：ARK_API_KEY + 模型 Endpoint ID + 火山 AK/SK。
追加：语音(ASR/TTS AppID+Token)、RTC(AppID/AppKey+对话式AI)、云手机(ACEP AK/SK/AccountID+TOS)、向量(VikingDB)、部署(veFaaS)。
